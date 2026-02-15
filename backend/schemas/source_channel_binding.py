from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SourceChannelBindingCreate(BaseModel):
    source_id: int
    channel_id: int


class SourceChannelBindingResponse(BaseModel):
    id: int
    source_id: int
    channel_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
