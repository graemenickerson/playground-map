from enum import StrEnum
from uuid import uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


UUID_V4_PATTERN = (
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class DatasetType(StrEnum):
    EQUIPMENT = "equipment"
    PARKS = "parks"
    SCHOOLS = "schools"


class SourceFeature(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
    )

    id: str = Field(
        alias="_id",
        default_factory=lambda: str(uuid4()),
        pattern=UUID_V4_PATTERN,
    )

    provider: str = Field(min_length=1)
    sourceService: str = Field(min_length=1)
    datasetType: DatasetType
    layerId: int | None = Field(ge=0)
    recordId: str = Field(min_length=1)
    attributes: dict[str, object]
    geometry: dict[str, object] | None
    importedAt: AwareDatetime

    def to_document(self) -> dict[str, object]:
        document = self.model_dump(by_alias=True, mode="python")
        document["datasetType"] = self.datasetType.value
        return document
