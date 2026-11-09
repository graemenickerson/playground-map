"""Validate query parameters for the playground list endpoint."""

from collections.abc import Mapping, Sequence
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AgeRange(StrEnum):
    AGES_2_TO_5 = "2-5"
    AGES_5_TO_12 = "5-12"


class PlaygroundListQuery(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
    )

    limit: int = Field(default=100, ge=1, le=500)
    q: str | None = Field(default=None, max_length=100)
    age: AgeRange | None = None
    washroom: bool = False


def parse_playground_list_query(
    parameters: Mapping[str, Sequence[str]],
) -> PlaygroundListQuery:
    values: dict[str, object] = {}

    for name, entries in parameters.items():
        if len(entries) != 1:
            raise ValueError(
                f"Query parameter '{name}' must appear exactly once"
            )

        value = entries[0]

        if name == "limit":
            try:
                values[name] = int(value)
            except ValueError:
                raise ValueError(
                    f"{name} must be an integer"
                ) from None

        elif name == "age":
            try:
                values[name] = AgeRange(value)
            except ValueError:
                raise ValueError(
                    "age must be '2-5' or '5-12'"
                ) from None

        elif name == "q":
            values[name] = value.strip() or None

        elif name == "washroom":
            if value not in {"true", "false"}:
                raise ValueError(
                    "washroom must be 'true' or 'false'"
                )

            values[name] = value == "true"

        else:
            values[name] = value

    return PlaygroundListQuery.model_validate(values)
