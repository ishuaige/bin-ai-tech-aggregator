from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class PushLogItem(Base):
    """推送日志明细：每条资讯一行，便于前端展示和筛选。"""

    __tablename__ = "push_log_items"
    __table_args__ = (
        Index("idx_push_log_items_push_log_id", "push_log_id"),
        Index("idx_push_log_items_hotness", "hotness"),
        Index("idx_push_log_items_author", "author_username"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    push_log_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("push_logs.id", ondelete="CASCADE"),
        nullable=False,
    )
    tweet_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    author_username: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    hotness: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ai_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
