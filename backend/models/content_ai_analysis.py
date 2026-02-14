from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class ContentAIAnalysis(Base):
    """通用资讯 AI 分析表：一条资讯对应一条最新分析。"""

    __tablename__ = "content_ai_analyses"
    __table_args__ = (
        CheckConstraint(
            "status in ('success', 'degraded', 'failed')",
            name="ck_content_ai_analyses_status",
        ),
        Index("idx_content_ai_analyses_content_item_id", "content_item_id", unique=True),
        Index("idx_content_ai_analyses_content_hash", "content_hash"),
        Index("idx_content_ai_analyses_updated_at", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    ai_score: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
