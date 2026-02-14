from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class LLMCallLog(Base):
    """记录每次大模型调用，方便后续做提示词优化分析。"""

    __tablename__ = "llm_call_logs"
    __table_args__ = (
        CheckConstraint(
            "status in ('success', 'degraded', 'failed')",
            name="ck_llm_call_logs_status",
        ),
        Index("idx_llm_call_logs_source_id", "source_id"),
        Index("idx_llm_call_logs_push_log_id", "push_log_id"),
        Index("idx_llm_call_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("monitor_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    push_log_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("push_logs.id", ondelete="SET NULL"),
        nullable=True,
    )
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
