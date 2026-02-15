from datetime import datetime

# Field 用于给字段添加额外的元数据（描述、默认值、校验规则等）
# 类似 Java Swagger 的 @Schema 或 @ApiModelProperty
from pydantic import BaseModel, Field


class CrawlItem(BaseModel):
    """统一抓取结果 DTO：后续 LLM/推送层只依赖这个结构。"""

    # Field(description="...") 用于生成 API 文档
    source: str = Field(description="来源类型，如 author_timeline / tweet_quotes")
    tweet_id: str = Field(description="推文 ID")
    author_username: str = Field(description="作者用户名")
    url: str = Field(description="推文链接")
    text: str = Field(description="推文正文")
    # datetime | None 表示可以为 null
    published_at: datetime | None = Field(default=None, description="推文发布时间")
    hotness: int | None = Field(default=None, description="热度分（0-100，规则计算）")
    # default_factory=dict: 默认值是一个空字典（注意：不能直接写 default={}，因为字典是可变对象）
    raw_payload: dict = Field(default_factory=dict, description="原始推文数据，便于调试和追溯")


class CrawlBatchResult(BaseModel):
    """一次抓取动作的统一返回结构。"""

    # list[CrawlItem]: 泛型列表，类似 List<CrawlItem>
    items: list[CrawlItem]
    next_cursor: str | None = None # 下一页游标
    has_next_page: bool = False    # 是否有下一页
