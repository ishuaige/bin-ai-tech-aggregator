from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models import PushStatus


class PushLogBase(BaseModel):
    source_id: int
    status: PushStatus
    created_at: datetime


class PushLogListItem(PushLogBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class PushLogDetail(PushLogListItem):
    raw_content: str | None
    ai_summary: str | None

    model_config = ConfigDict(from_attributes=True)
