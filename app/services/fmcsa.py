from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.carrier_check import CarrierCheck
from app.services.calls import get_or_create_call_session


class FMCSAClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def verify_carrier(self, db: Session, external_call_id: str, mc_number: str) -> dict[str, Any]:
        latest_cached = (
            db.query(CarrierCheck)
            .filter(CarrierCheck.mc_number == mc_number)
            .order_by(CarrierCheck.checked_at.desc())
            .first()
        )

        call_session = get_or_create_call_session(db=db, external_call_id=external_call_id)
        call_session.mc_number = mc_number

        try:
            if not self.settings.fmcsa_api_key:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="FMCSA API key is not configured.",
                )

            carrier_lookup = self._fetch_carrier_lookup(mc_number)
            carrier_record = carrier_lookup["carrier_record"]
            if not carrier_record:
                result = self._persist_check(
                    db=db,
                    mc_number=mc_number,
                    call_session=call_session,
                    verified=False,
                    eligible=False,
                    reasons=["Carrier not found for the provided MC number."],
                    snapshot={"docket_lookup": carrier_lookup["docket_payload"]},
                )
                return result

            carrier_details = self._fetch_carrier_details(carrier_lookup["dot_number"], carrier_record)
            evaluation = self._evaluate_carrier(
                dot_number=carrier_lookup["dot_number"],
                carrier_details=carrier_details["carrier_details"],
                basics_records=carrier_details["basics_records"],
                authority_record=carrier_details["authority_record"],
            )

            result = self._persist_check(
                db=db,
                mc_number=mc_number,
                call_session=call_session,
                verified=evaluation["verified"],
                eligible=evaluation["eligible"],
                reasons=evaluation["reasons"],
                snapshot={
                    "docket_lookup": carrier_lookup["docket_payload"],
                    "carrier": carrier_details["carrier_payload"],
                    "basics": carrier_details["basics_payload"],
                    "authority": carrier_details["authority_payload"],
                },
                dot_number=carrier_lookup["dot_number"],
                carrier_name=evaluation["carrier_name"],
                dba_name=evaluation["dba_name"],
                authority_status=evaluation["authority_status"],
                verification_source="live",
            )
            return result
        except HTTPException:
            raise
        except (httpx.HTTPError, ValueError):
            if latest_cached:
                return self._hydrate_cached_result(db=db, call_session=call_session, cached_check=latest_cached)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to verify carrier with FMCSA at this time.",
            )

    def _fetch_carrier_lookup(self, mc_number: str) -> dict[str, Any]:
        docket_payload = self._get(f"/carriers/docket-number/{mc_number}")
        carrier_record = self._pick_first_record(docket_payload)
        dot_number = None
        if carrier_record:
            dot_number = self._normalize_scalar(carrier_record.get("dotNumber") or carrier_record.get("dot_number"))

        return {
            "docket_payload": docket_payload,
            "carrier_record": carrier_record,
            "dot_number": dot_number,
        }

    def _fetch_carrier_details(self, dot_number: str | None, carrier_record: dict[str, Any]) -> dict[str, Any]:
        carrier_payload = self._get(f"/carriers/{dot_number}") if dot_number else {}
        carrier_details = self._pick_first_record(carrier_payload) or carrier_record
        basics_payload = self._get(f"/carriers/{dot_number}/basics") if dot_number else {}
        basics_records = self._coerce_list(basics_payload)
        authority_payload = self._get(f"/carriers/{dot_number}/authority") if dot_number else {}
        authority_record = self._pick_first_record(authority_payload) or authority_payload

        return {
            "carrier_payload": carrier_payload,
            "carrier_details": carrier_details,
            "basics_payload": basics_payload,
            "basics_records": basics_records,
            "authority_payload": authority_payload,
            "authority_record": authority_record,
        }

    def _evaluate_carrier(
        self,
        dot_number: str | None,
        carrier_details: dict[str, Any],
        basics_records: list[dict[str, Any]],
        authority_record: dict[str, Any] | list[Any],
    ) -> dict[str, Any]:
        authority_status = self._normalize_authority_status(authority_record)
        reasons = self._eligibility_reasons(
            carrier_details=carrier_details,
            basics_records=basics_records,
            authority_status=authority_status,
        )
        carrier_name = self._normalize_scalar(
            carrier_details.get("legalName") or carrier_details.get("legal_name") or carrier_details.get("dbaName")
        )
        return {
            "verified": bool(dot_number),
            "eligible": bool(dot_number) and not reasons,
            "reasons": reasons,
            "carrier_name": carrier_name,
            "dba_name": self._normalize_scalar(carrier_details.get("dbaName")),
            "authority_status": authority_status["label"],
        }

    def _get(self, path: str) -> dict[str, Any] | list[Any]:
        params = {"webKey": self.settings.fmcsa_api_key}
        with httpx.Client(base_url=self.settings.fmcsa_base_url, timeout=self.settings.request_timeout_seconds) as client:
            response = client.get(path, params=params)
            response.raise_for_status()
            return response.json()

    def _persist_check(
        self,
        db: Session,
        mc_number: str,
        call_session,
        verified: bool,
        eligible: bool,
        reasons: list[str],
        snapshot: dict[str, Any],
        dot_number: str | None = None,
        carrier_name: str | None = None,
        dba_name: str | None = None,
        authority_status: str | None = None,
        verification_source: str = "live",
    ) -> dict[str, Any]:
        carrier_check = CarrierCheck(
            mc_number=mc_number,
            dot_number=dot_number,
            legal_name=carrier_name,
            dba_name=dba_name,
            authority_status=authority_status,
            eligible=eligible,
            failure_reasons=reasons,
            snapshot=snapshot,
            verification_source=verification_source,
        )
        db.add(carrier_check)
        call_session.verification_passed = eligible
        db.add(call_session)
        db.commit()
        return {
            "verified": verified,
            "eligible": eligible,
            "carrier_name": carrier_name,
            "dot_number": dot_number,
            "authority_status": authority_status,
            "reasons": reasons,
            "summary_for_agent": self._agent_summary(verified=verified, eligible=eligible, carrier_name=carrier_name, reasons=reasons, cached=verification_source == "cached"),
        }

    def _hydrate_cached_result(self, db: Session, call_session, cached_check: CarrierCheck) -> dict[str, Any]:
        call_session.verification_passed = cached_check.eligible
        db.add(call_session)
        db.commit()
        return {
            "verified": bool(cached_check.dot_number),
            "eligible": cached_check.eligible,
            "carrier_name": cached_check.legal_name or cached_check.dba_name,
            "dot_number": cached_check.dot_number,
            "authority_status": cached_check.authority_status,
            "reasons": list(cached_check.failure_reasons),
            "summary_for_agent": self._agent_summary(
                verified=bool(cached_check.dot_number),
                eligible=cached_check.eligible,
                carrier_name=cached_check.legal_name or cached_check.dba_name,
                reasons=list(cached_check.failure_reasons),
                cached=True,
            ),
        }

    def _agent_summary(
        self,
        verified: bool,
        eligible: bool,
        carrier_name: str | None,
        reasons: list[str],
        cached: bool,
    ) -> str:
        carrier_label = carrier_name or "This carrier"
        if not verified:
            return f"{carrier_label} could not be verified with FMCSA."
        if eligible:
            suffix = " using cached FMCSA data." if cached else "."
            return f"{carrier_label} is verified and eligible to haul this load{suffix}"
        reason_text = "; ".join(reasons)
        return f"{carrier_label} is verified but not eligible: {reason_text}"

    def _eligibility_reasons(
        self,
        carrier_details: dict[str, Any],
        basics_records: list[dict[str, Any]],
        authority_status: dict[str, str | None],
    ) -> list[str]:
        reasons: list[str] = []

        if self._normalize_scalar(carrier_details.get("allowedToOperate") or carrier_details.get("allowToOperate")) != "Y":
            reasons.append("Carrier is not allowed to operate.")
        if self._normalize_scalar(carrier_details.get("outOfService")) == "Y":
            reasons.append("Carrier is currently out of service.")

        for basic in basics_records:
            basic_name = self._normalize_scalar(basic.get("basicShortDesc") or basic.get("basicDesc")) or "safety BASIC"
            if self._normalize_scalar(basic.get("svDeficient")) == "Y":
                reasons.append(f"{basic_name} shows a serious violation.")
            if self._normalize_scalar(basic.get("rdsvDeficient")) == "Y":
                reasons.append(f"{basic_name} exceeds the FMCSA threshold.")

        authority_key = authority_status["key"]
        authority_label = authority_status["label"]
        if authority_key == "active":
            return reasons
        if authority_label:
            reasons.append(f"Authority status is {authority_label.lower()}.")
        else:
            reasons.append("Authority status could not be confirmed.")

        return reasons

    def _normalize_authority_status(self, authority_record: dict[str, Any] | list[Any]) -> dict[str, str | None]:
        raw_status = self._extract_authority_status(authority_record)
        if raw_status is None:
            return {"key": None, "label": None}

        normalized = raw_status.strip()
        lowered = normalized.lower()
        if lowered in {"a", "active"}:
            return {"key": "active", "label": "Active"}
        if lowered in {"i", "inactive"}:
            return {"key": "inactive", "label": "Inactive"}
        return {"key": lowered, "label": normalized}

    def _extract_authority_status(self, authority_record: dict[str, Any] | list[Any]) -> str | None:
        if isinstance(authority_record, list):
            for item in authority_record:
                status = self._extract_authority_status(item)
                if status:
                    return status
            return None

        if not isinstance(authority_record, dict):
            return None

        # Unwrap nested carrierAuthority key if present
        if "carrierAuthority" in authority_record and isinstance(authority_record["carrierAuthority"], dict):
            return self._extract_authority_status(authority_record["carrierAuthority"])

        status_keys = (
            "commonAuthorityStatus",
            "contractAuthorityStatus",
            "brokerAuthorityStatus",
            "authorityStatus",
            "status",
        )
        for key in status_keys:
            value = self._normalize_scalar(authority_record.get(key))
            if value:
                return value

        for value in authority_record.values():
            if isinstance(value, str) and "active" in value.lower():
                return value
        return None

    def _pick_first_record(self, payload: dict[str, Any] | list[Any]) -> dict[str, Any] | None:
        data = self._unwrap_payload(payload)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    return self._extract_carrier(item)
            return None
        if isinstance(data, dict):
            return self._extract_carrier(data)
        return None

    def _extract_carrier(self, record: dict[str, Any]) -> dict[str, Any]:
        """Unwrap nested carrier key if present (FMCSA wraps carrier data inside a 'carrier' key)."""
        if "carrier" in record and isinstance(record["carrier"], dict):
            return record["carrier"]
        return record

    def _coerce_list(self, payload: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
        data = self._unwrap_payload(payload)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            return [data]
        return []

    def _unwrap_payload(self, payload: dict[str, Any] | list[Any]) -> Any:
        current = payload
        while isinstance(current, dict):
            for key in ("content", "results", "result", "data"):
                value = current.get(key)
                if value is not None:
                    current = value
                    break
            else:
                return current
        return current

    def _normalize_scalar(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return str(value)
