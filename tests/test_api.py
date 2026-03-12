import httpx

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


def test_healthcheck_reports_database(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_requires_api_key(client):
    response = client.get("/api/v1/metrics/summary")
    assert response.status_code == 401


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
            "outcome": "agreed",
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
    assert metrics["outcome_counts"]["agreed"] == 1
    assert metrics["sentiment_counts"]["positive"] == 1


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
