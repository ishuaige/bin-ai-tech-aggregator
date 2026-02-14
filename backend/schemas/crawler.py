from datetime import datetime

from pydantic import BaseModel, Field


class CrawlItem(BaseModel):
    """统一抓取结果 DTO：后续 LLM/推送层只依赖这个结构。"""

    source: str = Field(description="来源类型，如 author_timeline / tweet_quotes")
    tweet_id: str = Field(description="推文 ID")
    author_username: str = Field(description="作者用户名")
    url: str = Field(description="推文链接")
    text: str = Field(description="推文正文")
    published_at: datetime | None = Field(default=None, description="推文发布时间")
    raw_payload: dict = Field(default_factory=dict, description="原始推文数据，便于调试和追溯")


class CrawlBatchResult(BaseModel):
    """一次抓取动作的统一返回结构。"""

    items: list[CrawlItem]
    next_cursor: str | None = None
    has_next_page: bool = False
