import csv
import io
import logging
import math
import os
from datetime import datetime, timezone
from urllib.request import urlopen

from pymongo import MongoClient

from backend.source_models import DatasetType, SourceFeature


logger = logging.getLogger(__name__)

PROVIDER = "government_of_bc"
SOURCE_SERVICE = "schools_k12"

CSV_URL = (
    "https://catalogue.data.gov.bc.ca/dataset/"
    "95da1091-7e8c-4aa6-9c1b-5ab159ea7b42/resource/"
    "5832eff2-3380-435e-911b-5ada41c1d30b/download/"
    "bc_k12_schools_2026_databc_07_update.csv"
)

REQUIRED_COLUMNS = {
    "MINCODE",
    "SCHOOL_YEAR",
    "SCHOOL_NAME",
    "SCHOOL_EDUCATION_LEVEL",
    "STREET_ADDRESS",
    "PHYSICAL_ADDRESS_CITY",
    "ADDRESS_POSTAL_CODE",
    "LATITUDE",
    "LONGITUDE",
}


def fetch_rows() -> list[dict[str, str]]:
    with urlopen(CSV_URL, timeout=30) as response:
        with io.TextIOWrapper(response, encoding="utf-8-sig") as text:
            reader = csv.DictReader(text)
            missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])

            if missing:
                raise ValueError(
                    f"School CSV is missing columns: {sorted(missing)}"
                )

            rows = list(reader)

    if not rows:
        raise ValueError("School CSV contains no records")

    return rows


def school_geometry(row: dict[str, str]) -> dict | None:
    latitude = row["LATITUDE"].strip()
    longitude = row["LONGITUDE"].strip()

    if not latitude and not longitude:
        return None

    if not latitude or not longitude:
        raise ValueError("Only one coordinate is populated")

    lat = float(latitude)
    lng = float(longitude)

    if (
        not math.isfinite(lat)
        or not math.isfinite(lng)
        or not -90 <= lat <= 90
        or not -180 <= lng <= 180
    ):
        raise ValueError("Invalid school coordinates")

    return {
        "type": "Point",
        "coordinates": [lng, lat],
    }


def validate_rows(rows: list[dict[str, str]]) -> list[SourceFeature]:
    documents = []
    seen_ids = set()
    imported_at = datetime.now(timezone.utc)

    for row_number, row in enumerate(rows, start=2):
        record_id = row.get("MINCODE", "").strip()

        try:
            if (
                len(record_id) != 8
                or not record_id.isascii()
                or not record_id.isdigit()
            ):
                raise ValueError("MINCODE must contain eight digits")

            if record_id in seen_ids:
                raise ValueError(f"Duplicate MINCODE: {record_id}")

            seen_ids.add(record_id)

            document = SourceFeature.model_validate({
                "provider": PROVIDER,
                "sourceService": SOURCE_SERVICE,
                "datasetType": DatasetType.SCHOOLS,
                "layerId": None,
                "recordId": record_id,
                "attributes": row,
                "geometry": school_geometry(row),
                "importedAt": imported_at,
            })

        except (ValueError, TypeError, AttributeError):
            logger.error(
                "School validation failed: row=%s MINCODE=%r",
                row_number,
                record_id,
            )
            raise

        documents.append(document)

    return documents


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        documents = validate_rows(fetch_rows())
        missing_locations = sum(
            document.geometry is None for document in documents
        )

        logger.info(
            "Validated %s schools; %s without coordinates",
            len(documents),
            missing_locations,
        )

        uri = os.environ.get(
            "MONGODB_URI",
            "mongodb://127.0.0.1:27017",
        )
        database_name = os.environ.get(
            "MONGODB_DATABASE",
            "playground_app",
        )

        inserted = 0
        refreshed = 0

        with MongoClient(uri, serverSelectionTimeoutMS=3000) as client:
            database = client[database_name]

            if "source_features" not in database.list_collection_names():
                raise RuntimeError("Run db/init.js before importing")

            for feature in documents:
                document = feature.to_document()
                proposed_id = document.pop("_id")

                result = database.source_features.update_one(
                    {
                        "provider": document["provider"],
                        "sourceService": document["sourceService"],
                        "layerId": document["layerId"],
                        "recordId": document["recordId"],
                    },
                    {
                        "$set": document,
                        "$setOnInsert": {"_id": proposed_id},
                    },
                    upsert=True,
                )

                if result.upserted_id is not None:
                    inserted += 1
                else:
                    refreshed += 1

        logger.info(
            "School import complete: %s inserted, %s refreshed",
            inserted,
            refreshed,
        )

    except Exception:
        logger.exception("School import failed")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
