from typing import Literal

from pydantic import BaseModel, Field


class LLMSummaryResult(BaseModel):
    """大模型总结结果。"""

    status: Literal["success", "degraded", "failed"] = "success"
    summary_markdown: str = ""
    highlights: list[str] = Field(default_factory=list)
    failure_reason: str | None = None
