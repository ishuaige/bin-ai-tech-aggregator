from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class SourceChannelBinding(Base):
    """监控源与推送渠道绑定关系。"""

    __tablename__ = "source_channel_bindings"
    __table_args__ = (
        UniqueConstraint("source_id", "channel_id", name="uq_source_channel_bindings_pair"),
        Index("idx_source_channel_bindings_source_id", "source_id"),
        Index("idx_source_channel_bindings_channel_id", "channel_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("monitor_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("push_channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
