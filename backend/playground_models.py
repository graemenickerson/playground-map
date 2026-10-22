from enum import StrEnum
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
)

from backend.source_models import UUID_V4_PATTERN


UUIDString = Annotated[str, Field(pattern=UUID_V4_PATTERN)]


class SiteType(StrEnum):
    PARK = "park"
    POPUP = "popup"
    SCHOOL = "school"
    UNKNOWN = "unknown"


class Point(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["Point"] = "Point"
    coordinates: list[float] = Field(min_length=2, max_length=2)

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, value: list[float]) -> list[float]:
        longitude, latitude = value

        if not (
            -180 <= longitude <= 180
            and -90 <= latitude <= 90
        ):
            raise ValueError("Invalid longitude or latitude")

        return value


class Playground(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: UUIDString = Field(
        alias="_id",
        default_factory=lambda: str(uuid4()),
    )
    name: str | None = Field(default=None, min_length=1)
    siteType: SiteType = SiteType.UNKNOWN
    location: Point
    parkSourceId: UUIDString | None = None
    equipmentSourceIds: list[UUIDString] = Field(default_factory=list)

    @field_validator("siteType", mode="before")
    @classmethod
    def parse_site_type(cls, value: object) -> object:
        if isinstance(value, str):
            return SiteType(value)
        return value

    @field_serializer("siteType")
    def serialize_site_type(self, value: SiteType) -> str:
        return value.value

    def to_document(self) -> dict[str, object]:
        return self.model_dump(by_alias=True, mode="python")
