from typing import Literal

from pydantic import BaseModel, Field


class LLMInsightItem(BaseModel):
    """单条资讯洞察。"""

    tweet_id: str = ""
    ai_score: int = 0      # AI 评分
    summary: str = ""      # AI 总结摘要
    ai_title: str | None = None # AI 生成的标题


class LLMSummaryResult(BaseModel):
    """大模型总结结果。"""

    # Literal["..."]: 字面量类型，值只能是这几个字符串之一
    # 类似 Java 的 Enum，但在 Pydantic 中这样写更轻量，序列化直接是字符串
    status: Literal["success", "degraded", "failed"] = "success"
    summary_markdown: str = ""
    highlights: list[str] = Field(default_factory=list) # 亮点列表
    overall_score: int | None = None
    insights: list[LLMInsightItem] = Field(default_factory=list)
    model: str | None = None # 使用的模型名称
    prompt_text: str | None = None # 发送给 LLM 的提示词（用于调试）
    raw_response_text: str | None = None # LLM 的原始响应
    failure_reason: str | None = None # 失败原因


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
