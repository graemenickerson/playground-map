"""Build playground filters using imported park and equipment records."""

import re

from backend.request_models import PlaygroundListQuery


def matching_park_ids(sources, condition: dict) -> list[str]:
    return [
        park["_id"]
        for park in sources.find(
            {"datasetType": "parks", **condition},
            {"_id": 1},
        ).max_time_ms(3000)
    ]


def build_playground_filter(
    sources,
    query: PlaygroundListQuery,
) -> dict:
    conditions = []

    if query.q is not None:
        name_match = {
            "$regex": re.escape(query.q),
            "$options": "i",
        }

        park_ids = matching_park_ids(
            sources,
            {
                "$or": [
                    {"attributes.Park_Name": name_match},
                    {"attributes.Alias_Name": name_match},
                ]
            },
        )

        conditions.append({
            "$or": [
                {"name": name_match},
                {"parkSourceId": {"$in": park_ids}},
            ]
        })

    if query.age is not None:
        selected_minimum, selected_maximum = map(
            int,
            query.age.value.split("-"),
        )
        equipment_ids = []

        equipment = sources.find(
            {
                "datasetType": "equipment",
                "attributes.LifecycleStatus": "ACT",
                "attributes.PlayEquipmentAge": {"$type": "string"},
            },
            {"_id": 1, "attributes.PlayEquipmentAge": 1},
        ).max_time_ms(3000)

        for asset in equipment:
            age_range = asset["attributes"]["PlayEquipmentAge"]
            match = re.fullmatch(
                r"\s*(\d+)\s*-\s*(\d+)\s*",
                age_range,
            )

            if match is None:
                continue

            minimum, maximum = map(int, match.groups())

            if (
                minimum <= selected_minimum
                and maximum >= selected_maximum
            ):
                equipment_ids.append(asset["_id"])

        conditions.append({
            "equipmentSourceIds": {"$in": equipment_ids}
        })

    if query.washroom:
        park_ids = matching_park_ids(
            sources,
            {"attributes.Washroom": "Yes"},
        )
        conditions.append({
            "parkSourceId": {"$in": park_ids}
        })

    return {"$and": conditions} if conditions else {}
