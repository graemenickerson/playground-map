"""Preview playground groups from Victoria's imported equipment.

Groups equipment within the same park using a 15-metre connection
distance. Every pair in a proposed playground must also satisfy the
existing 50-metre maximum spread rule.

Skips groups containing already-assigned equipment. Reports equipment
without a unique park association and groups needing review.

Loads reviewed groups from playground_overrides.json before automatic
grouping. Their equipment is excluded from automatic grouping and review
output. Already-saved reviewed groups are skipped; ownership conflicts
stop the preview.

Prints candidate playground documents as JSON. Preview is the default.
Use --save to save all valid candidates, or --save-reviewed to save
reviewed groups only.
Use --review-output to also export review records to a JSON file.

Run from the project root:
    .venv/bin/python -m scripts.populate_playgrounds
"""

import argparse
import json
import logging
import os
from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from backend.playground_models import Point, SiteType, UUIDString
from scripts.build_playground import (
    MAX_EQUIPMENT_DISTANCE_METRES,
    build_playground,
    check_equipment_available,
    distance_metres,
)


logger = logging.getLogger(__name__)

GROUPING_DISTANCE_METRES = 15.0

SOURCE = {
    "provider": "city_of_victoria",
    "sourceService": "parks",
}


class ReviewedGroup(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    name: str | None = Field(min_length=1)
    siteType: SiteType
    parkSourceId: UUIDString | None
    equipmentSourceIds: list[UUIDString] = Field(min_length=1)
    maxEquipmentDistanceMetres: float = Field(
        default=MAX_EQUIPMENT_DISTANCE_METRES,
        gt=0,
        allow_inf_nan=False,
    )
    reviewNote: str = Field(min_length=1)


def group_equipment(assets: list[dict]) -> list[list[dict]]:
    assets = sorted(assets, key=lambda asset: asset["_id"])
    remaining = set(range(len(assets)))
    groups = []

    while remaining:
        first = min(remaining)
        remaining.remove(first)
        members = {first}
        pending = [first]

        while pending:
            current = pending.pop()
            nearby = {
                other
                for other in remaining
                if distance_metres(
                    assets[current]["geometry"]["coordinates"],
                    assets[other]["geometry"]["coordinates"],
                ) <= GROUPING_DISTANCE_METRES
            }

            remaining.difference_update(nearby)
            members.update(nearby)
            pending.extend(sorted(nearby))

        groups.append([assets[index] for index in sorted(members)])

    return groups


def review_record(asset: dict, reason: str, **context) -> dict:
    return {
        "equipmentId": asset["_id"],
        "sourceRecordId": asset["recordId"],
        "location": asset.get("geometry"),
        "reason": reason,
        **context,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preview playground candidates and equipment needing review."
    )
    parser.add_argument(
        "--review-output",
        type=Path,
        help="Optional destination for the generated review JSON.",
    )
    save_options = parser.add_mutually_exclusive_group()
    save_options.add_argument(
        "--save",
        action="store_true",
        help="Save all valid reviewed and automatic candidates.",
    )
    save_options.add_argument(
        "--save-reviewed",
        action="store_true",
        help="Save reviewed groups from playground_overrides.json.",
    )
    arguments = parser.parse_args()

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
        overrides_path = Path(__file__).with_name(
            "playground_overrides.json"
        )
        reviewed_groups = TypeAdapter(
            list[ReviewedGroup]
        ).validate_json(overrides_path.read_text(encoding="utf-8"))

        reviewed_ids = set()

        for group in reviewed_groups:
            for equipment_id in group.equipmentSourceIds:
                if equipment_id in reviewed_ids:
                    raise ValueError(
                        f"Equipment appears more than once in overrides: "
                        f"{equipment_id}"
                    )
                reviewed_ids.add(equipment_id)

        with MongoClient(uri, serverSelectionTimeoutMS=3000) as client:
            database = client[database_name]

            required = {"source_features", "playgrounds"}
            if not required.issubset(database.list_collection_names()):
                raise RuntimeError("Run db/init.js first")

            sources = database.source_features
            equipment_by_park = defaultdict(list)
            parks = {}
            unresolved_assets = 0
            needs_review = []
            already_assigned = []
            assigned_ids = {
                equipment_id
                for playground in database.playgrounds.find(
                    {},
                    {"equipmentSourceIds": 1},
                )
                for equipment_id in playground.get("equipmentSourceIds", [])
            }

            candidates = []
            reviewed_candidates = []

            for group in reviewed_groups:
                existing = database.playgrounds.find_one({
                    "equipmentSourceIds": {
                        "$all": group.equipmentSourceIds,
                        "$size": len(group.equipmentSourceIds),
                    },
                    "name": group.name,
                    "siteType": group.siteType.value,
                    "parkSourceId": group.parkSourceId,
                })

                if existing is not None:
                    already_assigned.append({
                        "parkSourceId": group.parkSourceId,
                        "equipmentIds": sorted(group.equipmentSourceIds),
                    })
                    logger.info(
                        "Reviewed group already saved: name=%r",
                        group.name,
                    )
                    continue

                check_equipment_available(
                    database.playgrounds,
                    group.equipmentSourceIds,
                )

                playground = build_playground(
                    sources,
                    group.equipmentSourceIds,
                    group.parkSourceId,
                    group.name,
                    site_type=group.siteType,
                    max_equipment_distance_metres=(
                        group.maxEquipmentDistanceMetres
                    ),
                )
                candidates.append(playground.to_document())
                reviewed_candidates.append(playground.to_document())

                logger.info(
                    "Reviewed candidate: name=%r equipment=%s note=%s",
                    group.name,
                    len(group.equipmentSourceIds),
                    group.reviewNote,
                )

            for asset in sources.find({
                **SOURCE,
                "datasetType": "equipment",
                "attributes.LifecycleStatus": "ACT",
            }):
                if asset["_id"] in reviewed_ids:
                    continue

                try:
                    point = Point.model_validate(asset.get("geometry"))
                except ValueError:
                    unresolved_assets += 1
                    needs_review.append(review_record(
                        asset,
                        "invalid_location",
                    ))
                    logger.warning(
                        "Review equipment record=%s: invalid location",
                        asset["recordId"],
                    )
                    continue

                matches = list(sources.find({
                    **SOURCE,
                    "datasetType": "parks",
                    "geometry": {
                        "$geoIntersects": {
                            "$geometry": point.model_dump()
                        }
                    },
                }))

                if len(matches) != 1:
                    unresolved_assets += 1
                    needs_review.append(review_record(
                        asset,
                        "no_park_match" if not matches else "multiple_park_matches",
                        candidateParkIds=[park["_id"] for park in matches],
                    ))
                    logger.warning(
                        "Review equipment record=%s: park matches=%s",
                        asset["recordId"],
                        len(matches),
                    )
                    continue

                park = matches[0]
                parks[park["_id"]] = park
                equipment_by_park[park["_id"]].append(asset)

            skipped_groups = 0

            for park_id in sorted(equipment_by_park):
                park = parks[park_id]
                park_name = park["attributes"].get("Park_Name")
                groups = group_equipment(equipment_by_park[park_id])

                for number, group in enumerate(groups, start=1):
                    equipment_ids = [asset["_id"] for asset in group]
                    used_ids = set(equipment_ids).intersection(assigned_ids)

                    if used_ids:
                        skipped_groups += 1
                        already_assigned.append({
                            "parkSourceId": park_id,
                            "equipmentIds": sorted(used_ids),
                        })

                        for asset in group:
                            if asset["_id"] not in used_ids:
                                needs_review.append(review_record(
                                    asset,
                                    "group_contains_assigned_equipment",
                                    parkSourceId=park_id,
                                    groupEquipmentIds=equipment_ids,
                                ))

                        logger.info(
                            "Skipped park=%r group=%s: "
                            "%s of %s equipment records already assigned",
                            park_name,
                            number,
                            len(used_ids),
                            len(group),
                        )
                        continue

                    name = park_name

                    if name and len(groups) > 1:
                        name = f"{name} - {number}"

                    try:
                        check_equipment_available(
                            database.playgrounds,
                            equipment_ids,
                        )

                        playground = build_playground(
                            sources,
                            equipment_ids,
                            park_id,
                            name,
                        )
                    except ValueError as error:
                        skipped_groups += 1
                        needs_review.extend(
                            review_record(
                                asset,
                                "group_validation_failed",
                                details=str(error),
                                parkSourceId=park_id,
                                groupEquipmentIds=equipment_ids,
                            )
                            for asset in group
                        )
                        logger.warning(
                            "Skipped park=%r group=%s: %s",
                            park_name,
                            number,
                            error,
                        )
                        continue

                    logger.info(
                        "Candidate: name=%r equipment=%s sourceRecords=%s",
                        name,
                        len(group),
                        [asset["recordId"] for asset in group],
                    )
                    candidates.append(playground.to_document())

            if arguments.save or arguments.save_reviewed:
                documents_to_save = (
                    candidates
                    if arguments.save
                    else reviewed_candidates
                )

                index = database.playgrounds.index_information().get(
                    "unique_playground_equipment"
                )
                if not index or not index.get("unique"):
                    raise RuntimeError(
                        "Equipment ownership index is missing; "
                        "run db/init.js first"
                    )

                for document in documents_to_save:
                    check_equipment_available(
                        database.playgrounds,
                        document["equipmentSourceIds"],
                    )

                    try:
                        database.playgrounds.insert_one(document)
                    except DuplicateKeyError as error:
                        raise ValueError(
                            "Save conflicts with an existing playground; "
                            "equipment may have been assigned "
                            "by another process"
                        ) from error

                    logger.info(
                        "Saved playground: id=%s name=%r",
                        document["_id"],
                        document["name"],
                    )

                logger.info(
                    "Saved %s playgrounds",
                    len(documents_to_save),
                )
            else:
                logger.info("Preview only. No database writes.")

            logger.info(
                "Population complete: %s candidates, %s skipped groups, "
                "%s unresolved equipment records.",
                len(candidates),
                skipped_groups,
                unresolved_assets,
            )

            logger.info(
                "%s equipment records need review",
                len(needs_review),
            )

            if arguments.review_output is not None:
                destination = arguments.review_output
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(
                    json.dumps(needs_review, indent=2) + "\n",
                    encoding="utf-8",
                )
                logger.info(
                    "Exported %s review records to %s",
                    len(needs_review),
                    destination,
                )

            print(json.dumps({
                "candidates": candidates,
                "needsReview": needs_review,
                "alreadyAssigned": already_assigned,
            }, indent=2))

    except ValueError as error:
        logger.error("%s", error)
        raise SystemExit(1)

    except Exception:
        logger.exception("Playground population failed")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
