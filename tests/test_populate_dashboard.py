from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from fastapi import HTTPException, status

from app.dependencies import get_fmcsa_client


_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "populate_dashboard.py"
_SPEC = importlib.util.spec_from_file_location("populate_dashboard", _SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load populate_dashboard module from {_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)
populate_dashboard = _MODULE.populate_dashboard


class EligibleFMCSAClient:
    def verify_carrier(self, db, external_call_id: str, mc_number: str):
        from app.models.carrier_check import CarrierCheck
        from app.services.calls import get_or_create_call_session

        call_session = get_or_create_call_session(db, external_call_id)
        call_session.mc_number = mc_number
        call_session.verification_passed = True
        db.add(call_session)
        db.add(
            CarrierCheck(
                mc_number=mc_number,
                dot_number="123456",
                legal_name="Acme Carrier LLC",
                authority_status="ACTIVE",
                eligible=True,
                failure_reasons=[],
                snapshot={"source": "fake-live"},
                verification_source="live",
            )
        )
        db.commit()
        return {
            "verified": True,
            "eligible": True,
            "carrier_name": "Acme Carrier LLC",
            "dot_number": "123456",
            "authority_status": "ACTIVE",
            "reasons": [],
            "summary_for_agent": "Acme Carrier LLC is verified and eligible to haul this load.",
        }


class UnavailableFMCSAClient:
    def verify_carrier(self, db, external_call_id: str, mc_number: str):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FMCSA API key is not configured.",
        )


def test_populate_dashboard_generates_completed_and_pending_calls_without_fmcsa(client):
    client.app.dependency_overrides[get_fmcsa_client] = lambda: UnavailableFMCSAClient()

    report = populate_dashboard(client, api_key="test-api-key", run_prefix="seed-no-fmcsa")

    assert len(report.created_call_ids) >= 6
    assert any(scenario.status == "pending" for scenario in report.scenarios)
    assert "booked" in report.metrics["outcome_counts"]
    assert "rejected_rate" in report.metrics["outcome_counts"]
    assert "no_match" in report.metrics["outcome_counts"]
    assert "other" in report.metrics["outcome_counts"]
    assert report.metrics["verified_calls"] == 0

    recent_calls = report.dashboard["recent_calls"]
    assert any(call["ended_at"] is None for call in recent_calls)
    assert any(call["outcome"] == "booked" for call in recent_calls)
    assert any(call["outcome"] == "rejected_rate" for call in recent_calls)
    assert any(call["outcome"] == "no_match" for call in recent_calls)
    assert any(call["outcome"] == "other" for call in recent_calls)

    skipped = {scenario.name for scenario in report.skipped_scenarios}
    assert "verified_pending_search" in skipped


def test_populate_dashboard_records_verified_pending_calls_when_fmcsa_is_available(client):
    client.app.dependency_overrides[get_fmcsa_client] = lambda: EligibleFMCSAClient()

    report = populate_dashboard(client, api_key="test-api-key", run_prefix="seed-with-fmcsa")

    assert report.metrics["verified_calls"] > 0
    verified_call = next(
        call for call in report.dashboard["recent_calls"] if call["external_call_id"] == "seed-with-fmcsa-verified-pending-search"
    )
    assert verified_call["verification_passed"] is True
    assert verified_call["ended_at"] is None
    assert verified_call["selected_load"] is not None


def test_populate_dashboard_is_append_only_across_runs(client):
    client.app.dependency_overrides[get_fmcsa_client] = lambda: UnavailableFMCSAClient()

    first_report = populate_dashboard(client, api_key="test-api-key", run_prefix="seed-first")
    second_report = populate_dashboard(client, api_key="test-api-key", run_prefix="seed-second")

    assert set(first_report.created_call_ids).isdisjoint(second_report.created_call_ids)
    assert len(second_report.dashboard["recent_calls"]) > 0
    assert second_report.metrics["total_calls"] >= len(first_report.created_call_ids) + len(second_report.created_call_ids)

    first_booked_loads = {
        scenario.load_id
        for scenario in first_report.scenarios
        if scenario.name in {"booked_after_two_counters", "booked_at_list"} and scenario.load_id is not None
    }
    second_booked_loads = {
        scenario.load_id
        for scenario in second_report.scenarios
        if scenario.name in {"booked_after_two_counters", "booked_at_list"} and scenario.load_id is not None
    }
    assert first_booked_loads.isdisjoint(second_booked_loads)
