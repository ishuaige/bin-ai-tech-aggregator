from datetime import datetime

from pydantic import BaseModel


class ContentAnalysisInfo(BaseModel):
    status: str
    ai_score: int
    summary: str
    model: str
    updated_at: datetime
    failure_reason: str | None = None


class ContentListItem(BaseModel):
    id: int
    platform: str
    source_type: str
    external_id: str
    author_name: str
    url: str
    title: str | None = None
    content_text: str
    hotness: int
    published_at: datetime | None = None
    created_at: datetime
    ai: ContentAnalysisInfo | None = None
