import logging
import os
from collections import Counter, defaultdict

from pymongo import MongoClient


logger = logging.getLogger(__name__)

SOURCE = {
    "provider": "city_of_victoria",
    "sourceService": "parks",
}


def normalize_name(value: object) -> str:
    if not isinstance(value, str):
        return ""

    return " ".join(value.casefold().split())


def examine_geometry(collection, equipment, parks_by_name) -> None:
    counts = Counter()

    for asset in equipment:
        point = asset.get("geometry")

        if not isinstance(point, dict) or point.get("type") != "Point":
            counts["missing_point"] += 1
            logger.warning(
                "Missing point geometry: record=%s",
                asset["recordId"],
            )
            continue

        spatial_matches = list(collection.find(
            {
                **SOURCE,
                "datasetType": "parks",
                "geometry": {
                    "$geoIntersects": {"$geometry": point}
                },
            },
            {
                "_id": 1,
                "recordId": 1,
                "attributes.Park_Name": 1,
            },
        ))

        name = normalize_name(
            asset["attributes"].get("LocationName")
        )
        name_matches = parks_by_name.get(name, {})

        if not spatial_matches:
            outcome = "no_spatial_match"
        elif len(spatial_matches) > 1:
            outcome = "multiple_spatial_matches"
        elif len(name_matches) == 1:
            spatial_id = spatial_matches[0]["_id"]
            outcome = (
                "agreement"
                if spatial_id in name_matches
                else "conflict"
            )
        else:
            outcome = "spatial_candidate"

        counts[outcome] += 1

        if outcome != "agreement":
            logger.info(
                "Spatial review: record=%s name=%r outcome=%s "
                "name_candidates=%s spatial_candidates=%s",
                asset["recordId"],
                asset["attributes"].get("LocationName"),
                outcome,
                [
                    park["recordId"]
                    for park in name_matches.values()
                ],
                [
                    {
                        "recordId": park["recordId"],
                        "name": park["attributes"].get("Park_Name"),
                    }
                    for park in spatial_matches
                ],
            )

    logger.info("Spatial comparison summary: %s", dict(counts))


def examine(collection) -> None:
    parks = list(collection.find({
        **SOURCE,
        "datasetType": "parks",
    }))

    equipment = list(collection.find({
        **SOURCE,
        "datasetType": "equipment",
    }))

    parks_by_name = defaultdict(dict)

    for park in parks:
        attributes = park["attributes"]

        for field in ("Park_Name", "Alias_Name"):
            name = normalize_name(attributes.get(field))

            if name:
                parks_by_name[name][park["_id"]] = park

    counts = Counter()
    equipment_by_park = Counter()
    matched_parks = {}

    logger.info(
        "Examining %s equipment records against %s park records",
        len(equipment),
        len(parks),
    )

    for asset in equipment:
        attributes = asset["attributes"]
        original_name = attributes.get("LocationName")
        name = normalize_name(original_name)
        matches = list(parks_by_name.get(name, {}).values())

        if not name:
            counts["missing_name"] += 1
            logger.warning(
                "Missing name: record=%s uuid=%s",
                asset["recordId"],
                asset["_id"],
            )

        elif not matches:
            counts["unmatched"] += 1
            logger.warning(
                "No park match: record=%s name=%r",
                asset["recordId"],
                original_name,
            )

        elif len(matches) > 1:
            counts["ambiguous"] += 1
            candidates = [
                {
                    "recordId": park["recordId"],
                    "name": park["attributes"].get("Park_Name"),
                }
                for park in matches
            ]
            logger.warning(
                "Multiple matches: record=%s name=%r candidates=%s",
                asset["recordId"],
                original_name,
                candidates,
            )

        else:
            counts["matched"] += 1
            park = matches[0]
            equipment_by_park[park["_id"]] += 1
            matched_parks[park["_id"]] = park

    logger.info(
        "Summary: matched=%s unmatched=%s ambiguous=%s missing_name=%s",
        counts["matched"],
        counts["unmatched"],
        counts["ambiguous"],
        counts["missing_name"],
    )

    logger.info("Equipment counts by uniquely matched park:")

    for park_id, count in equipment_by_park.most_common():
        park = matched_parks[park_id]
        attributes = park["attributes"]

        logger.info(
            "Park=%r record=%s equipment=%s PlayEquipment=%r",
            attributes.get("Park_Name"),
            park["recordId"],
            count,
            attributes.get("PlayEquipment"),
        )

    examine_geometry(collection, equipment, parks_by_name)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    uri = os.environ.get(
        "MONGODB_URI",
        "mongodb://127.0.0.1:27017",
    )
    database_name = os.environ.get(
        "MONGODB_DATABASE",
        "playground_app",
    )

    try:
        with MongoClient(uri, serverSelectionTimeoutMS=3000) as client:
            database = client[database_name]

            if "source_features" not in database.list_collection_names():
                raise RuntimeError("source_features collection is missing")

            examine(database.source_features)

    except Exception:
        logger.exception("Database examination failed")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
