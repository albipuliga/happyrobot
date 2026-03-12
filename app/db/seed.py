import json
from datetime import datetime
from pathlib import Path

from app.db.session import get_session_factory
from app.models.load import Load


def seed_loads_if_empty() -> None:
    session_factory = get_session_factory()
    with session_factory() as db:
        if db.query(Load).count() > 0:
            return

        seed_path = Path(__file__).resolve().parents[2] / "data" / "loads.json"
        with seed_path.open("r", encoding="utf-8") as seed_file:
            raw_loads = json.load(seed_file)

        loads = [
            Load(
                load_id=item["load_id"],
                origin=item["origin"],
                destination=item["destination"],
                pickup_datetime=datetime.fromisoformat(item["pickup_datetime"]),
                delivery_datetime=datetime.fromisoformat(item["delivery_datetime"]),
                equipment_type=item["equipment_type"],
                loadboard_rate=item["loadboard_rate"],
                max_rate=item["max_rate"],
                notes=item["notes"],
                weight=item["weight"],
                commodity_type=item["commodity_type"],
                num_of_pieces=item["num_of_pieces"],
                miles=item["miles"],
                dimensions=item["dimensions"],
                status=item.get("status", "available"),
                broker_notes=item.get("broker_notes"),
            )
            for item in raw_loads
        ]
        db.add_all(loads)
        db.commit()
