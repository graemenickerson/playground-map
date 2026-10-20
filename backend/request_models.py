"""Validate query parameters for the playground list endpoint."""

from collections.abc import Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field


class PlaygroundListQuery(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
    )

    limit: int = Field(default=100, ge=1, le=500)


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
                    "limit must be an integer between 1 and 500"
                ) from None
        else:
            values[name] = value

    return PlaygroundListQuery.model_validate(values)
