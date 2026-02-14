from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class ContentItem(Base):
    """通用资讯主表：支持 Twitter/Reddit/RSS 等多来源。"""

    __tablename__ = "content_items"
    __table_args__ = (
        Index("idx_content_items_platform_external", "platform", "external_id", unique=True),
        Index("idx_content_items_source_type", "source_type"),
        Index("idx_content_items_author", "author_name"),
        Index("idx_content_items_published_at", "published_at"),
        Index("idx_content_items_updated_at", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, default="twitter")
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    author_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    hotness: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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
