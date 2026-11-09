"""Local read-only API for saved playgrounds.

Run from the project root:
    .venv/bin/flask --app backend.app run --debug --port 5001
"""

import os

from flask import Flask, jsonify, request
from pydantic import ValidationError
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from werkzeug.exceptions import HTTPException

from backend.playground_models import Playground
from backend.playground_queries import build_playground_filter
from backend.request_models import parse_playground_list_query


def create_app() -> Flask:
    app = Flask(__name__)

    client = MongoClient(
        os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017"),
        serverSelectionTimeoutMS=3000,
        socketTimeoutMS=5000,
    )
    database = client[
        os.environ.get("MONGODB_DATABASE", "playground_app")
    ]

    app.extensions["mongo_client"] = client

    def error_response(code: str, message: str, status: int):
        return jsonify(
            error={"code": code, "message": message}
        ), status

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.get("/api/playgrounds")
    def list_playgrounds():
        try:
            query = parse_playground_list_query(
                request.args.to_dict(flat=False)
            )
        except ValidationError:
            return error_response(
                "invalid_request",
                "Supported parameters: q (up to 100 characters), "
                "age ('2-5' or '5-12'), washroom ('true' or 'false'), "
                "and limit (integer 1–500).",
                400,
            )
        except ValueError as error:
            return error_response(
                "invalid_request",
                str(error),
                400,
            )

        playground_filter = build_playground_filter(
            database.source_features,
            query,
        )

        documents = list(
            database.playgrounds.find(playground_filter)
            .sort("_id", 1)
            .limit(query.limit + 1)
            .max_time_ms(3000)
        )

        items = [
            Playground.model_validate(document).model_dump(
                by_alias=True,
                mode="json",
                exclude={"equipmentSourceIds"},
            )
            for document in documents[:query.limit]
        ]

        return jsonify(
            items=items,
            limit=query.limit,
            hasMore=len(documents) > query.limit,
        )

    @app.errorhandler(ConnectionFailure)
    def database_unavailable(error):
        app.logger.exception("MongoDB connection failed")
        return error_response(
            "database_unavailable",
            "The database is currently unavailable.",
            503,
        )

    @app.errorhandler(HTTPException)
    def http_error(error):
        return error_response(
            error.name.lower().replace(" ", "_"),
            error.description,
            error.code,
        )

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.exception("Unexpected API failure")
        return error_response(
            "internal_error",
            "The request could not be completed.",
            500,
        )

    return app
