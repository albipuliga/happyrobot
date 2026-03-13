from datetime import datetime, timedelta

import httpx
import pytest

from app.dependencies import get_fmcsa_client
from app.models.carrier_check import CarrierCheck
from app.models.call_session import CallSession
from app.models.load import Load
from app.models.negotiation_event import NegotiationEvent
from app.services.fmcsa import FMCSAClient


class FakeFMCSAClient:
    def __init__(self):
        self.raise_timeout = False

    def verify_carrier(self, db, external_call_id: str, mc_number: str):
        if self.raise_timeout:
            raise RuntimeError("timeout")
        from app.services.calls import get_or_create_call_session
        from app.models.carrier_check import CarrierCheck

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
                snapshot={"source": "fake"},
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


def _auth_headers():
    return {"X-API-Key": "test-api-key"}


def test_normalize_postgres_database_urls():
    from app.db.session import normalize_database_url

    assert normalize_database_url("postgres://user:pass@localhost:5432/happyrobot") == (
        "postgresql+psycopg://user:pass@localhost:5432/happyrobot"
    )
    assert normalize_database_url("postgresql://user:pass@localhost:5432/happyrobot") == (
        "postgresql+psycopg://user:pass@localhost:5432/happyrobot"
    )
    assert normalize_database_url("postgresql+psycopg://user:pass@localhost:5432/happyrobot") == (
        "postgresql+psycopg://user:pass@localhost:5432/happyrobot"
    )


def test_healthcheck_reports_database(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_requires_api_key(client):
    response = client.get("/api/v1/metrics/summary")
    assert response.status_code == 401


def test_dashboard_page_returns_html_without_api_key(client):
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Dashboard Access" in response.text


def test_dashboard_data_requires_dashboard_login(client):
    response = client.get("/dashboard/data")

    assert response.status_code == 401
    assert response.json()["detail"] == "Dashboard authentication required."


def test_dashboard_login_rejects_wrong_password(client):
    response = client.post("/dashboard/login", json={"password": "wrong-password"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid password."

    page_response = client.get("/dashboard")
    assert page_response.status_code == 200
    assert "Dashboard Access" in page_response.text


def test_dashboard_login_unlocks_page_and_data(client):
    login_response = client.post("/dashboard/login", json={"password": "test-api-key"})

    assert login_response.status_code == 200
    assert login_response.json() == {"success": True}

    page_response = client.get("/dashboard")
    assert page_response.status_code == 200
    assert '<div class="dashboard-shell">' in page_response.text

    data_response = client.get("/dashboard/data")
    assert data_response.status_code == 200
    body = data_response.json()
    assert body["summary"]["total_calls"] == 0
    assert body["summary"]["agreements"] == 0
    assert body["outcome_breakdown"] == []
    assert body["sentiment_breakdown"] == []
    assert body["recent_calls"] == []
    assert body["load_status_counts"]["available"] > 0
    assert body["load_status_breakdown"] == [{"label": "available", "count": body["load_status_counts"]["available"], "tone": "pending"}]
    assert body["last_updated_at"] is not None


def test_verify_carrier_success(client):
    fake = FakeFMCSAClient()
    client.app.dependency_overrides[get_fmcsa_client] = lambda: fake

    response = client.post(
        "/api/v1/carriers/verify",
        headers=_auth_headers(),
        json={"external_call_id": "call-1", "mc_number": "12345"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is True
    assert body["dot_number"] == "123456"


@pytest.mark.parametrize("mc_number", [None, "", "   ", "null"])
def test_verify_carrier_rejects_invalid_mc_number(client, mc_number):
    response = client.post(
        "/api/v1/carriers/verify",
        headers=_auth_headers(),
        json={"external_call_id": "call-invalid", "mc_number": mc_number},
    )

    assert response.status_code == 422


def test_search_loads_returns_ranked_matches(client):
    response = client.post(
        "/api/v1/loads/search",
        headers=_auth_headers(),
        json={
            "external_call_id": "call-2",
            "equipment_type": "Dry Van",
            "origin": "Dallas",
            "destination": "Atlanta",
            "pickup_date": "2026-03-13",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["matches"]) == 3
    assert body["best_match"]["load_id"] == "ACM-1001"


def test_search_loads_no_match(client):
    response = client.post(
        "/api/v1/loads/search",
        headers=_auth_headers(),
        json={
            "external_call_id": "call-3",
            "equipment_type": "Step Deck",
            "origin": "Dallas",
            "destination": "Atlanta",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["matches"] == []
    assert body["best_match"] is None


def test_search_loads_clears_selected_load_when_no_match(client):
    first_response = client.post(
        "/api/v1/loads/search",
        headers=_auth_headers(),
        json={
            "external_call_id": "call-search-state",
            "equipment_type": "Dry Van",
            "origin": "Dallas",
            "destination": "Atlanta",
            "pickup_date": "2026-03-13",
        },
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/api/v1/loads/search",
        headers=_auth_headers(),
        json={
            "external_call_id": "call-search-state",
            "equipment_type": "Step Deck",
            "origin": "Dallas",
            "destination": "Atlanta",
        },
    )
    assert second_response.status_code == 200
    assert second_response.json()["matches"] == []

    login_response = client.post("/dashboard/login", json={"password": "test-api-key"})
    assert login_response.status_code == 200

    dashboard_response = client.get("/dashboard/data")
    assert dashboard_response.status_code == 200

    recent_call = next(
        item for item in dashboard_response.json()["recent_calls"] if item["external_call_id"] == "call-search-state"
    )
    assert recent_call["matched_loads_count"] == 0
    assert recent_call["selected_load"] is None


def test_negotiation_accepts_after_second_counter(client):
    first = client.post(
        "/api/v1/loads/negotiate",
        headers=_auth_headers(),
        json={"external_call_id": "call-4", "load_id": "ACM-1001", "carrier_offer": 2700},
    )
    assert first.status_code == 200
    assert first.json()["decision"] == "countered"
    assert first.json()["broker_offer"] == 2350

    second = client.post(
        "/api/v1/loads/negotiate",
        headers=_auth_headers(),
        json={"external_call_id": "call-4", "load_id": "ACM-1001", "carrier_offer": 2425},
    )
    assert second.status_code == 200
    assert second.json()["decision"] == "countered"
    assert second.json()["broker_offer"] == 2450

    third = client.post(
        "/api/v1/loads/negotiate",
        headers=_auth_headers(),
        json={"external_call_id": "call-4", "load_id": "ACM-1001", "carrier_offer": 2450},
    )
    assert third.status_code == 200
    assert third.json()["decision"] == "accepted"
    assert third.json()["transfer_ready"] is True


def test_negotiation_rejects_after_round_three(client):
    for index in range(1, 4):
        response = client.post(
            "/api/v1/loads/negotiate",
            headers=_auth_headers(),
            json={"external_call_id": "call-5", "load_id": "ACM-1002", "carrier_offer": 2600 + index * 10},
        )
        assert response.status_code == 200
        assert response.json()["decision"] == "countered"

    final_response = client.post(
        "/api/v1/loads/negotiate",
        headers=_auth_headers(),
        json={"external_call_id": "call-5", "load_id": "ACM-1002", "carrier_offer": 2800},
    )

    assert final_response.status_code == 200
    assert final_response.json()["decision"] == "rejected"
    assert final_response.json()["attempts_remaining"] == 0


def test_negotiation_rejects_pending_transfer_load(client):
    complete_response = client.post(
        "/api/v1/calls/complete",
        headers=_auth_headers(),
        json={
            "external_call_id": "call-pending-transfer",
            "load_id": "ACM-1001",
            "final_rate": 2300,
            "outcome": "booked",
            "sentiment": "positive",
        },
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["load_status"] == "pending_transfer"

    negotiation_response = client.post(
        "/api/v1/loads/negotiate",
        headers=_auth_headers(),
        json={"external_call_id": "call-second-carrier", "load_id": "ACM-1001", "carrier_offer": 2400},
    )
    assert negotiation_response.status_code == 409
    assert negotiation_response.json()["detail"] == "Load is no longer open for negotiation."


def test_complete_call_marks_load_pending_transfer_and_updates_metrics(client):
    verify_client = FakeFMCSAClient()
    client.app.dependency_overrides[get_fmcsa_client] = lambda: verify_client

    verify_response = client.post(
        "/api/v1/carriers/verify",
        headers=_auth_headers(),
        json={"external_call_id": "call-6", "mc_number": "55555"},
    )
    assert verify_response.status_code == 200

    complete_response = client.post(
        "/api/v1/calls/complete",
        headers=_auth_headers(),
        json={
            "external_call_id": "call-6",
            "mc_number": "55555",
            "load_id": "ACM-1001",
            "final_rate": 2300,
            "outcome": "booked",
            "sentiment": "positive",
            "transcript_excerpt": "Carrier accepted the load at 2300.",
            "extracted_fields": {"carrier_name": "Acme Carrier LLC"},
        },
    )

    assert complete_response.status_code == 200
    assert complete_response.json()["load_status"] == "pending_transfer"

    metrics_response = client.get("/api/v1/metrics/summary", headers=_auth_headers())
    assert metrics_response.status_code == 200
    metrics = metrics_response.json()
    assert metrics["agreements"] == 1
    assert metrics["transfers_ready"] == 1
    assert metrics["outcome_counts"]["booked"] == 1
    assert metrics["sentiment_counts"]["positive"] == 1

    login_response = client.post("/dashboard/login", json={"password": "test-api-key"})
    assert login_response.status_code == 200

    dashboard_response = client.get("/dashboard/data")
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["summary"]["agreements"] == 1
    assert dashboard["summary"]["outcome_counts"]["booked"] == 1
    assert dashboard["summary"]["sentiment_counts"]["positive"] == 1


def test_complete_call_canonicalizes_legacy_classifier_aliases(client):
    from app.config import get_settings
    from app.db.session import get_session_factory

    response = client.post(
        "/api/v1/calls/complete",
        headers=_auth_headers(),
        json={
            "external_call_id": "call-legacy-aliases",
            "load_id": "ACM-1001",
            "final_rate": 2200,
            "outcome": "accepted",
            "sentiment": "mixed",
        },
    )

    assert response.status_code == 200
    assert response.json()["load_status"] == "pending_transfer"

    metrics_response = client.get("/api/v1/metrics/summary", headers=_auth_headers())
    assert metrics_response.status_code == 200
    metrics = metrics_response.json()
    assert metrics["agreements"] == 1
    assert metrics["outcome_counts"]["booked"] == 1
    assert metrics["sentiment_counts"]["neutral"] == 1

    session_factory = get_session_factory(get_settings().database_url)
    with session_factory() as db:
        call_session = db.query(CallSession).filter(CallSession.external_call_id == "call-legacy-aliases").one()
        assert call_session.outcome == "booked"
        assert call_session.sentiment == "neutral"


def test_complete_call_rejects_unknown_classifier_labels(client):
    response = client.post(
        "/api/v1/calls/complete",
        headers=_auth_headers(),
        json={
            "external_call_id": "call-invalid-classification",
            "outcome": "price_pending",
            "sentiment": "happy",
        },
    )

    assert response.status_code == 422


def test_metrics_and_dashboard_bucket_dirty_state_values_as_unknown(client):
    from app.config import get_settings
    from app.db.session import get_session_factory

    session_factory = get_session_factory(get_settings().database_url)
    with session_factory() as db:
        dirty_load = db.query(Load).filter(Load.load_id == "ACM-1001").one()
        dirty_load.status = "covered"
        dirty_call = CallSession(
            external_call_id="call-dirty-states",
            mc_number="90909",
            selected_load=dirty_load,
            matched_loads_count=1,
            agreed_rate=2200,
            outcome="accepted",
            sentiment="mixed",
            ended_at=datetime.utcnow(),
        )
        db.add_all([dirty_load, dirty_call])
        db.commit()

    metrics_response = client.get("/api/v1/metrics/summary", headers=_auth_headers())
    assert metrics_response.status_code == 200
    metrics = metrics_response.json()
    assert metrics["agreements"] == 0
    assert metrics["transfers_ready"] == 0
    assert metrics["outcome_counts"] == {"unknown": 1}
    assert metrics["sentiment_counts"] == {"unknown": 1}

    login_response = client.post("/dashboard/login", json={"password": "test-api-key"})
    assert login_response.status_code == 200

    dashboard_response = client.get("/dashboard/data")
    assert dashboard_response.status_code == 200
    body = dashboard_response.json()
    assert body["summary"]["agreements"] == 0
    assert body["summary"]["transfers_ready"] == 0
    assert body["summary"]["outcome_counts"] == {"unknown": 1}
    assert body["summary"]["sentiment_counts"] == {"unknown": 1}
    assert body["load_status_counts"]["unknown"] == 1
    assert {item["label"]: item["tone"] for item in body["outcome_breakdown"]} == {"unknown": "pending"}
    assert {item["label"]: item["tone"] for item in body["sentiment_breakdown"]} == {"unknown": "pending"}
    assert {item["label"]: item["tone"] for item in body["load_status_breakdown"]}["unknown"] == "pending"

    recent_call = next(item for item in body["recent_calls"] if item["external_call_id"] == "call-dirty-states")
    assert recent_call["outcome"] == "unknown"
    assert recent_call["outcome_tone"] == "pending"
    assert recent_call["sentiment"] == "unknown"
    assert recent_call["sentiment_tone"] == "pending"
    assert recent_call["selected_load"]["status"] == "unknown"


def test_fmcsa_authority_status_rules():
    client = FMCSAClient(settings=type("SettingsStub", (), {"app_api_key": "x"})())

    active_status = client._normalize_authority_status({"authorityStatus": "Active"})
    assert active_status == {"key": "active", "label": "Active"}
    assert client._eligibility_reasons(
        carrier_details={"allowedToOperate": "Y", "outOfService": "N"},
        basics_records=[],
        authority_status=active_status,
    ) == []

    code_active_status = client._normalize_authority_status({"authorityStatus": "A"})
    assert code_active_status == {"key": "active", "label": "Active"}
    assert client._eligibility_reasons(
        carrier_details={"allowedToOperate": "Y", "outOfService": "N"},
        basics_records=[],
        authority_status=code_active_status,
    ) == []

    inactive_status = client._normalize_authority_status({"authorityStatus": "Inactive"})
    assert inactive_status == {"key": "inactive", "label": "Inactive"}
    assert client._eligibility_reasons(
        carrier_details={"allowedToOperate": "Y", "outOfService": "N"},
        basics_records=[],
        authority_status=inactive_status,
    ) == ["Authority status is inactive."]

    code_inactive_status = client._normalize_authority_status({"authorityStatus": "I"})
    assert code_inactive_status == {"key": "inactive", "label": "Inactive"}
    assert client._eligibility_reasons(
        carrier_details={"allowedToOperate": "Y", "outOfService": "N"},
        basics_records=[],
        authority_status=code_inactive_status,
    ) == ["Authority status is inactive."]

    missing_status = client._normalize_authority_status({})
    assert missing_status == {"key": None, "label": None}
    assert client._eligibility_reasons(
        carrier_details={"allowedToOperate": "Y", "outOfService": "N"},
        basics_records=[],
        authority_status=missing_status,
    ) == ["Authority status could not be confirmed."]


def test_dashboard_data_includes_recent_calls_sorted_by_recency(client):
    from app.config import get_settings
    from app.db.session import get_session_factory

    login_response = client.post("/dashboard/login", json={"password": "test-api-key"})
    assert login_response.status_code == 200

    verify_client = FakeFMCSAClient()
    client.app.dependency_overrides[get_fmcsa_client] = lambda: verify_client

    verify_response = client.post(
        "/api/v1/carriers/verify",
        headers=_auth_headers(),
        json={"external_call_id": "call-dashboard-1", "mc_number": "10101"},
    )
    assert verify_response.status_code == 200

    first_counter = client.post(
        "/api/v1/loads/negotiate",
        headers=_auth_headers(),
        json={"external_call_id": "call-dashboard-1", "load_id": "ACM-1001", "carrier_offer": 2700},
    )
    assert first_counter.status_code == 200

    second_counter = client.post(
        "/api/v1/loads/negotiate",
        headers=_auth_headers(),
        json={"external_call_id": "call-dashboard-1", "load_id": "ACM-1001", "carrier_offer": 2425},
    )
    assert second_counter.status_code == 200

    complete_first = client.post(
        "/api/v1/calls/complete",
        headers=_auth_headers(),
        json={
            "external_call_id": "call-dashboard-1",
            "mc_number": "10101",
            "load_id": "ACM-1001",
            "final_rate": 2450,
            "outcome": "booked",
            "sentiment": "positive",
            "transcript_excerpt": "Carrier accepted after the second counter.",
            "extracted_fields": {"dispatcher": "Mila"},
        },
    )
    assert complete_first.status_code == 200

    complete_second = client.post(
        "/api/v1/calls/complete",
        headers=_auth_headers(),
        json={
            "external_call_id": "call-dashboard-2",
            "mc_number": "",
            "load_id": "",
            "final_rate": "",
            "outcome": "rejected_rate",
            "sentiment": "negative",
            "transcript_excerpt": "",
            "extracted_fields": {},
        },
    )
    assert complete_second.status_code == 200

    session_factory = get_session_factory(get_settings().database_url)
    with session_factory() as db:
        older_call = db.query(CallSession).filter(CallSession.external_call_id == "call-dashboard-1").one()
        newer_call = db.query(CallSession).filter(CallSession.external_call_id == "call-dashboard-2").one()
        older_call.updated_at = datetime.utcnow() - timedelta(minutes=10)
        newer_call.updated_at = datetime.utcnow()
        db.add_all([older_call, newer_call])
        db.commit()

    response = client.get("/dashboard/data?limit=2")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_calls"] == 2
    assert body["summary"]["agreements"] == 1
    assert body["summary"]["transfers_ready"] == 1
    assert body["summary"]["outcome_counts"]["booked"] == 1
    assert body["summary"]["outcome_counts"]["rejected_rate"] == 1
    assert body["summary"]["sentiment_counts"]["negative"] == 1
    assert body["load_status_counts"]["pending_transfer"] == 1
    assert {item["label"]: item["tone"] for item in body["outcome_breakdown"]} == {
        "booked": "positive",
        "rejected_rate": "negative",
    }
    assert {item["label"]: item["tone"] for item in body["sentiment_breakdown"]} == {
        "positive": "positive",
        "negative": "negative",
    }
    assert {item["label"]: item["tone"] for item in body["load_status_breakdown"]}["pending_transfer"] == "positive"

    recent_calls = body["recent_calls"]
    assert [call["external_call_id"] for call in recent_calls] == ["call-dashboard-2", "call-dashboard-1"]

    latest_call = recent_calls[0]
    assert latest_call["selected_load"] is None
    assert latest_call["agreed_rate"] is None
    assert latest_call["transcript_excerpt"] is None
    assert latest_call["negotiation_rounds"] == 0
    assert latest_call["verification_tone"] == "pending"
    assert latest_call["outcome_tone"] == "negative"
    assert latest_call["sentiment_tone"] == "negative"

    earlier_call = recent_calls[1]
    assert earlier_call["selected_load"]["load_id"] == "ACM-1001"
    assert earlier_call["selected_load"]["status"] == "pending_transfer"
    assert earlier_call["agreed_rate"] == 2450
    assert earlier_call["negotiation_rounds"] == 2
    assert earlier_call["transcript_excerpt"] == "Carrier accepted after the second counter."
    assert earlier_call["verification_tone"] == "positive"
    assert earlier_call["outcome_tone"] == "positive"
    assert earlier_call["sentiment_tone"] == "positive"


def test_fmcsa_timeout_uses_cached_result(client):
    from app.config import Settings, get_settings
    from app.db.session import get_session_factory

    get_settings.cache_clear()
    session_factory = get_session_factory(get_settings().database_url)

    with session_factory() as db:
        db.add(
            CarrierCheck(
                mc_number="77777",
                dot_number="654321",
                legal_name="Cached Carrier Inc.",
                authority_status="ACTIVE",
                eligible=True,
                failure_reasons=[],
                snapshot={"source": "cached"},
                verification_source="cached",
            )
        )
        db.commit()

        service = FMCSAClient(Settings(fmcsa_api_key="test-key"))

        def fail_request(_: FMCSAClient, path: str):
            raise httpx.ReadTimeout(f"timeout for {path}")

        service._get = fail_request.__get__(service, FMCSAClient)
        result = service.verify_carrier(db=db, external_call_id="call-7", mc_number="77777")

    assert result["eligible"] is True
    assert result["carrier_name"] == "Cached Carrier Inc."
    assert "cached" in result["summary_for_agent"].lower()
