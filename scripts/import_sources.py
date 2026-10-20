import logging
import os
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import urlopen
import json

from pydantic import ValidationError
from pymongo import MongoClient

from backend.source_models import DatasetType, SourceFeature


logger = logging.getLogger(__name__)

PROVIDER = "city_of_victoria"
SOURCE_SERVICE = "parks"
DATASETS = {
    DatasetType.EQUIPMENT: 20,
    DatasetType.PARKS: 50,
}
SERVICE_URL = (
    "https://maps.victoria.ca/server/rest/services/"
    "OpenData/OpenData_Parks/MapServer"
)


def fetch_features(layer_id: int) -> list[dict]:
    features = []
    offset = 0

    while True:
        parameters = urlencode({
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": 4326,
            "f": "geojson",
            "orderByFields": "OBJECTID",
            "resultOffset": offset,
            "resultRecordCount": 1000,
        })

        with urlopen(
            f"{SERVICE_URL}/{layer_id}/query?{parameters}",
            timeout=30,
        ) as response:
            payload = json.load(response)

        if payload.get("type") != "FeatureCollection":
            raise ValueError("City API did not return a FeatureCollection")

        batch = payload["features"]
        features.extend(batch)

        if not payload.get("exceededTransferLimit") and len(batch) < 1000:
            return features

        if not batch:
            raise ValueError("City API returned an incomplete result")

        offset += len(batch)


def validate_features(
    features: list[dict],
    dataset_type: DatasetType,
    layer_id: int,
) -> list[SourceFeature]:
    validated = []
    seen_ids = set()
    imported_at = datetime.now(timezone.utc)

    for feature in features:
        attributes = feature.get("properties", {})
        record_id = attributes.get("OBJECTID")

        if type(record_id) is not int:
            raise ValueError("Source record has a missing or invalid OBJECTID")

        if record_id in seen_ids:
            raise ValueError(f"Duplicate source OBJECTID: {record_id}")

        seen_ids.add(record_id)

        try:
            document = SourceFeature.model_validate({
                "provider": PROVIDER,
                "sourceService": SOURCE_SERVICE,
                "datasetType": dataset_type,
                "layerId": layer_id,
                "recordId": str(record_id),
                "attributes": attributes,
                "geometry": feature.get("geometry"),
                "importedAt": imported_at,
            })
        except ValidationError as error:
            logger.error(
                "Validation failed: dataset=%s layer=%s record=%s errors=%s",
                dataset_type,
                layer_id,
                record_id,
                error.errors(include_input=False, include_url=False),
            )
            raise

        validated.append(document)

    return validated


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        documents: list[SourceFeature] = []

        for dataset_type, layer_id in DATASETS.items():
            features = fetch_features(layer_id)
            validated = validate_features(
                features,
                dataset_type,
                layer_id,
            )
            documents.extend(validated)
            logger.info(
                "Validated %s %s records",
                len(validated),
                dataset_type,
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
        updated = 0

        with MongoClient(uri, serverSelectionTimeoutMS=3000) as client:
            database = client[database_name]

            if "source_features" not in database.list_collection_names():
                raise RuntimeError("Run db/init.js before importing")

            collection = database.source_features

            for feature in documents:
                document = feature.to_document()
                proposed_id = document.pop("_id")

                result = collection.update_one(
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
                    updated += 1

        logger.info(
            "Import complete: %s source records inserted, %s refreshed",
            inserted,
            updated,
        )

    except Exception:
        logger.exception("Import failed")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
