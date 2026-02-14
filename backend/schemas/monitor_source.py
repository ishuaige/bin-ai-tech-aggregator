from pydantic import BaseModel, ConfigDict, Field

from models import SourceType


class MonitorSourceBase(BaseModel):
    type: SourceType
    value: str = Field(min_length=1, max_length=100)
    is_active: bool = True
    remark: str | None = Field(default=None, max_length=255)


class MonitorSourceCreate(MonitorSourceBase):
    pass


class MonitorSourceUpdate(BaseModel):
    type: SourceType | None = None
    value: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None
    remark: str | None = Field(default=None, max_length=255)


class MonitorSourceResponse(MonitorSourceBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
