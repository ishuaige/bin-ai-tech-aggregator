from typing import Literal

from pydantic import BaseModel, Field


class LLMInsightItem(BaseModel):
    """单条资讯洞察。"""

    tweet_id: str = ""
    ai_score: int = 0
    summary: str = ""
    ai_title: str | None = None


class LLMSummaryResult(BaseModel):
    """大模型总结结果。"""

    status: Literal["success", "degraded", "failed"] = "success"
    summary_markdown: str = ""
    highlights: list[str] = Field(default_factory=list)
    overall_score: int | None = None
    insights: list[LLMInsightItem] = Field(default_factory=list)
    model: str | None = None
    prompt_text: str | None = None
    raw_response_text: str | None = None
    failure_reason: str | None = None


class LLMItemAnalysisResult(BaseModel):
    """单条资讯分析结果（用于 AI 缓存与调用日志）。"""

    status: Literal["success", "degraded", "failed"] = "success"
    insight: LLMInsightItem | None = None
    model: str | None = None
    prompt_text: str | None = None
    raw_response_text: str | None = None
    failure_reason: str | None = None


class LLMBatchItemAnalysisResult(BaseModel):
    """多条资讯批量分析结果。"""

    status: Literal["success", "degraded", "failed"] = "success"
    insights: list[LLMInsightItem] = Field(default_factory=list)
    model: str | None = None
    prompt_text: str | None = None
    raw_response_text: str | None = None
    failure_reason: str | None = None
