"""Seed the dashboard with sample calls for local development."""

from __future__ import annotations

import os
import sys
from uuid import uuid4

import httpx

BASE_URL = os.getenv("HAPPYROBOT_BASE_URL", "http://127.0.0.1:8000")


def api_post(client: httpx.Client, path: str, data: dict) -> dict:
    r = client.post(path, json=data, headers=client.headers)
    r.raise_for_status()
    return r.json()


def api_get(client: httpx.Client, path: str) -> dict:
    r = client.get(path, headers=client.headers)
    r.raise_for_status()
    return r.json()


def main() -> int:
    api_key = os.getenv("APP_API_KEY")
    if not api_key:
        print("APP_API_KEY is required.", file=sys.stderr)
        return 1

    prefix = f"seed-{uuid4().hex[:8]}"
    headers = {"Accept": "application/json", "Content-Type": "application/json", "X-API-Key": api_key}

    with httpx.Client(base_url=BASE_URL, headers=headers, follow_redirects=True, timeout=30.0) as c:
        api_get(c, "/health")

        # --- 1. Booked after 2 negotiation rounds (positive) ---
        cid = f"{prefix}-1"
        search = api_post(c, "/api/v1/loads/search", {
            "external_call_id": cid, "equipment_type": "Dry Van",
            "origin": "Dallas", "destination": "Atlanta", "pickup_date": "2026-03-13",
        })
        load = search["best_match"]
        lid, rate = load["load_id"], int(load["loadboard_rate"])
        r1 = api_post(c, "/api/v1/loads/negotiate", {"external_call_id": cid, "load_id": lid, "carrier_offer": rate + 500})
        r2 = api_post(c, "/api/v1/loads/negotiate", {"external_call_id": cid, "load_id": lid, "carrier_offer": int(r1["broker_offer"]) + 75})
        accepted_rate = int(r2["broker_offer"])
        api_post(c, "/api/v1/calls/complete", {
            "external_call_id": cid, "mc_number": "MC-245901", "load_id": lid,
            "final_rate": accepted_rate, "outcome": "booked", "sentiment": "positive",
            "transcript_excerpt": "Dispatcher pushed back once, then accepted when the carrier's next offer landed inside the broker's concession range.",
            "extracted_fields": {"scenario": "booked_after_two_rounds", "negotiation_style": "firm_but_fair"},
        })
        print(f"  1. Booked after 2 rounds @ ${accepted_rate}")

        # --- 2. Booked at list rate (neutral) ---
        cid = f"{prefix}-2"
        search = api_post(c, "/api/v1/loads/search", {
            "external_call_id": cid, "equipment_type": "Reefer",
            "origin": "Chicago", "destination": "Memphis", "pickup_date": "2026-03-13",
        })
        load = search["best_match"]
        lid, rate = load["load_id"], int(load["loadboard_rate"])
        api_post(c, "/api/v1/loads/negotiate", {"external_call_id": cid, "load_id": lid, "carrier_offer": rate})
        api_post(c, "/api/v1/calls/complete", {
            "external_call_id": cid, "mc_number": "MC-188204", "load_id": lid,
            "final_rate": rate, "outcome": "booked", "sentiment": "neutral",
            "transcript_excerpt": "Carrier accepted the posted rate without a counter and moved straight to dispatch details.",
            "extracted_fields": {"scenario": "booked_at_list", "negotiation_style": "straight_accept"},
        })
        print(f"  2. Booked at list rate ${rate}")

        # --- 3. Rejected after max negotiation rounds (negative) ---
        cid = f"{prefix}-3"
        search = api_post(c, "/api/v1/loads/search", {
            "external_call_id": cid, "equipment_type": "Flatbed",
            "origin": "Los Angeles", "destination": "Phoenix", "pickup_date": "2026-03-13",
        })
        load = search["best_match"]
        lid, rate = load["load_id"], int(load["loadboard_rate"])
        r1 = api_post(c, "/api/v1/loads/negotiate", {"external_call_id": cid, "load_id": lid, "carrier_offer": rate + 500})
        r2 = api_post(c, "/api/v1/loads/negotiate", {"external_call_id": cid, "load_id": lid, "carrier_offer": int(r1["broker_offer"]) + 125})
        r3 = api_post(c, "/api/v1/loads/negotiate", {"external_call_id": cid, "load_id": lid, "carrier_offer": int(r2["broker_offer"]) + 125})
        r4 = api_post(c, "/api/v1/loads/negotiate", {"external_call_id": cid, "load_id": lid, "carrier_offer": int(r3["broker_offer"]) + 150})
        api_post(c, "/api/v1/calls/complete", {
            "external_call_id": cid, "mc_number": "MC-330118", "load_id": lid,
            "final_rate": None, "outcome": "rejected_rate", "sentiment": "negative",
            "transcript_excerpt": "Carrier stayed above the final approved rate and ended the call after the last counter.",
            "extracted_fields": {"scenario": "rejected_after_max_rounds", "final_counter": r4["broker_offer"]},
        })
        print(f"  3. Rejected after max rounds (ceiling ${r4['broker_offer']})")

        # --- 4. No matching load (neutral) ---
        cid = f"{prefix}-4"
        api_post(c, "/api/v1/loads/search", {
            "external_call_id": cid, "equipment_type": "Step Deck",
            "origin": "Dallas", "destination": "Atlanta", "pickup_date": "2026-03-13",
        })
        api_post(c, "/api/v1/calls/complete", {
            "external_call_id": cid, "mc_number": "MC-410220", "load_id": None,
            "final_rate": None, "outcome": "no_match", "sentiment": "neutral",
            "transcript_excerpt": "Carrier was looking for a step deck reload, but nothing fit the lane and date window.",
            "extracted_fields": {"scenario": "no_match", "requested_equipment": "Step Deck"},
        })
        print("  4. No match (Step Deck)")

        # --- 5. Carrier ineligible (negative) ---
        cid = f"{prefix}-5"
        verify = api_post(c, "/api/v1/carriers/verify", {"external_call_id": cid, "mc_number": "12345"})
        reasons = verify.get("reasons", [])
        api_post(c, "/api/v1/calls/complete", {
            "external_call_id": cid, "mc_number": "12345", "load_id": None,
            "final_rate": None, "outcome": "carrier_ineligible", "sentiment": "negative",
            "transcript_excerpt": f"Carrier could not be cleared to book freight: {'; '.join(reasons) or 'ineligible'}.",
            "extracted_fields": {"fmcsa_reasons": reasons},
        })
        print(f"  5. Carrier ineligible ({len(reasons)} reasons)")

        # --- 6. Callback / other (neutral) ---
        cid = f"{prefix}-6"
        search = api_post(c, "/api/v1/loads/search", {
            "external_call_id": cid, "equipment_type": "Dry Van",
            "origin": "Savannah", "destination": "Birmingham", "pickup_date": "2026-03-15",
        })
        lid = search["best_match"]["load_id"]
        api_post(c, "/api/v1/calls/complete", {
            "external_call_id": cid, "mc_number": "MC-509901", "load_id": lid,
            "final_rate": None, "outcome": "other", "sentiment": "neutral",
            "transcript_excerpt": "Dispatcher liked the lane but asked for a rate sheet by email and a callback after the current delivery.",
            "extracted_fields": {"scenario": "other_callback", "follow_up_channel": "email"},
        })
        print("  6. Callback requested (other)")

        # --- 7. Verified + searched, left pending ---
        cid = f"{prefix}-7"
        try:
            api_post(c, "/api/v1/carriers/verify", {"external_call_id": cid, "mc_number": "MC-245901"})
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (502, 503):
                print("  7. Verify unavailable (FMCSA down), skipping pending scenario")
            else:
                raise
        else:
            api_post(c, "/api/v1/loads/search", {
                "external_call_id": cid, "equipment_type": "Dry Van",
                "origin": "Columbus", "destination": "Allentown", "pickup_date": "2026-03-15",
            })
            print("  7. Verified + searched (pending)")

        # --- Summary ---
        api_post(c, "/dashboard/login", {"password": api_key})
        data = api_get(c, "/dashboard/data?limit=10&offset=0")
        print(f"\nDashboard seeded: {data.get('total_calls', '?')} total calls")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
