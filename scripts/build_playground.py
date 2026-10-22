"""Build and print a playground document from imported equipment records.

Accepts equipment UUIDs from source_features, an optional park UUID, and
an optional display name. Validates the selected records and checks that
equipment lies within the park when one is supplied.

Rejects selections where any equipment pair exceeds the maximum spread.
The default is 50 metres; reviewed groups can supply a different limit
when calling build_playground.
Uses the average equipment coordinates as an approximate playground pin.
Prints JSON to stdout and logs to stderr. Preview is the default.
Pass --save to insert the playground into MongoDB.
Site type defaults to park when a park is supplied, otherwise unknown.
Use --site-type to explicitly select park, popup, school, or unknown.
Equipment already assigned to a playground cannot be reused.
Each successful build generates a new playground UUID.

Run from the project root:
    .venv/bin/python -m scripts.build_playground \\
        --equipment-ids UUID-1 UUID-2 \\
        --park-id PARK-UUID \\
        --name "Chapman Street Playlot"
"""

import argparse
import json
import logging
import math
import os
from itertools import combinations

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from backend.playground_models import Playground, Point, SiteType


logger = logging.getLogger(__name__)

MAX_EQUIPMENT_DISTANCE_METRES = 50.0


def distance_metres(first: list[float], second: list[float]) -> float:
    longitude1, latitude1 = map(math.radians, first)
    longitude2, latitude2 = map(math.radians, second)

    delta_latitude = latitude2 - latitude1
    delta_longitude = longitude2 - longitude1

    haversine = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(latitude1)
        * math.cos(latitude2)
        * math.sin(delta_longitude / 2) ** 2
    )

    return 2 * 6_371_000 * math.asin(
        math.sqrt(min(1.0, max(0.0, haversine)))
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build playground JSON from imported source records."
    )
    parser.add_argument(
        "--equipment-ids",
        nargs="+",
        required=True,
        help="Equipment UUIDs from source_features.",
    )
    parser.add_argument(
        "--park-id",
        help="Optional park UUID from source_features.",
    )
    parser.add_argument(
        "--name",
        help="Optional display name; otherwise use the park name if available.",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save the validated playground; otherwise only print JSON.",
    )
    parser.add_argument(
        "--site-type",
        choices=[category.value for category in SiteType],
        help="Optional category; defaults to park with --park-id, otherwise unknown.",
    )
    return parser.parse_args()


def build_playground(
    sources,
    equipment_ids: list[str],
    park_id: str | None,
    name: str | None,
    site_type: SiteType | None = None,
    *,
    max_equipment_distance_metres: float = MAX_EQUIPMENT_DISTANCE_METRES,
) -> Playground:
    if (
        isinstance(max_equipment_distance_metres, bool)
        or not isinstance(max_equipment_distance_metres, (int, float))
        or not math.isfinite(max_equipment_distance_metres)
        or max_equipment_distance_metres <= 0
    ):
        raise ValueError(
            "Maximum equipment distance must be a positive finite number"
        )

    if not equipment_ids:
        raise ValueError("At least one equipment ID is required")

    if len(set(equipment_ids)) != len(equipment_ids):
        raise ValueError("Equipment IDs must not contain duplicates")

    equipment = list(sources.find({
        "_id": {"$in": equipment_ids},
        "datasetType": "equipment",
    }))

    found_ids = {asset["_id"] for asset in equipment}
    missing_ids = set(equipment_ids) - found_ids

    if missing_ids:
        raise ValueError(
            f"Missing equipment records or wrong dataset type: "
            f"{sorted(missing_ids)}"
        )

    park = None

    if park_id is not None:
        park = sources.find_one({
            "_id": park_id,
            "datasetType": "parks",
        })

        if park is None:
            raise ValueError("Park record is missing or has the wrong type")

    points = []

    for asset in equipment:
        point = Point.model_validate(asset["geometry"])

        if park is not None:
            park_match = sources.find_one({
                "_id": park["_id"],
                "geometry": {
                    "$geoIntersects": {
                        "$geometry": point.model_dump()
                    }
                },
            })

            if park_match is None:
                raise ValueError(
                    f"Equipment {asset['_id']} is outside the selected park"
                )

        points.append(point.coordinates)

    for first, second in combinations(range(len(points)), 2):
        distance = distance_metres(points[first], points[second])

        if distance > max_equipment_distance_metres:
            raise ValueError(
                f"Equipment {equipment[first]['_id']} and "
                f"{equipment[second]['_id']} are {distance:.2f} metres "
                f"apart; maximum allowed distance is "
                f"{max_equipment_distance_metres:g} metres"
            )

    location = Point(coordinates=[
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    ])

    if name is None and park is not None:
        name = park["attributes"].get("Park_Name")

    return Playground(
        name=name,
        siteType=(
            site_type
            if site_type is not None
            else SiteType.PARK if park is not None else SiteType.UNKNOWN
        ),
        location=location,
        parkSourceId=park_id,
        equipmentSourceIds=sorted(equipment_ids),
    )


def check_equipment_available(collection, equipment_ids: list[str]) -> None:
    conflicts = list(collection.find(
        {"equipmentSourceIds": {"$in": equipment_ids}},
        {"_id": 1, "equipmentSourceIds": 1},
    ))

    if conflicts:
        selected = set(equipment_ids)
        details = [
            f"Playground {document['_id']}\n"
            "    Equipment: "
            + ", ".join(sorted(
                selected.intersection(document["equipmentSourceIds"])
            ))
            for document in conflicts
        ]
        raise ValueError(
            "Selected equipment already belongs to a playground:\n"
            + "\n".join(f"  {detail}" for detail in details)
            + "\nNo playground was saved."
        )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )
    arguments = parse_arguments()

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

            required = {"source_features", "playgrounds"}
            if not required.issubset(database.list_collection_names()):
                raise RuntimeError("Run db/init.js first")

            playground = build_playground(
                database.source_features,
                arguments.equipment_ids,
                arguments.park_id,
                arguments.name,
                site_type=(
                    SiteType(arguments.site_type)
                    if arguments.site_type is not None
                    else None
                ),
            )

            check_equipment_available(
                database.playgrounds,
                playground.equipmentSourceIds,
            )

            if arguments.save:
                index = database.playgrounds.index_information().get(
                    "unique_playground_equipment"
                )
                if not index or not index.get("unique"):
                    raise RuntimeError(
                        "Equipment ownership index is missing; "
                        "run db/init.js first"
                    )

                try:
                    database.playgrounds.insert_one(
                        playground.to_document()
                    )
                except DuplicateKeyError as error:
                    raise ValueError(
                        "Save conflicts with an existing playground; "
                        "equipment may have been assigned by another process"
                    ) from error

        logger.info(
            "%s playground from %s equipment records",
            "Saved" if arguments.save else "Previewed; no database writes:",
            len(playground.equipmentSourceIds),
        )
        print(json.dumps(playground.to_document(), indent=2))

    except ValueError as error:
        logger.error("%s", error)
        raise SystemExit(1)

    except Exception:
        logger.exception("Playground build failed")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
