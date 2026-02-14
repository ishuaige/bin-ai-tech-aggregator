from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from models.enums import PushStatus


class PushLog(Base):
    """推送日志表：记录每次抓取/总结/推送的执行结果。"""

    __tablename__ = "push_logs"
    __table_args__ = (
        CheckConstraint(
            "status in ('success', 'failed')",
            name="ck_push_logs_status",
        ),
        Index("idx_push_logs_source_id", "source_id"),
        Index("idx_push_logs_status", "status"),
        Index("idx_push_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 外键 (ForeignKey)
    # ForeignKey("monitor_sources.id"): 关联 monitor_sources 表的 id 字段
    # ondelete="CASCADE": 级联删除，如果源被删了，日志也一起删
    source_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("monitor_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Text: 长文本类型 (对应 MySQL TEXT / PostgreSQL TEXT)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    status: Mapped[PushStatus] = mapped_column(
        Enum(
            PushStatus,
            name="push_status",
            native_enum=False,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    
    # DateTime: 时间类型
    # func.now(): 数据库函数 NOW()，由数据库生成默认时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    
    # 关系映射 (Relationship) - 这纯粹是 ORM层面的概念，不影响数据库结构
    # 允许你通过 push_log.source 直接访问 MonitorSource 对象
    # back_populates="logs" 表示 MonitorSource 类里如果有一个 logs 属性，它们会自动关联
    # 类似 Java JPA @ManyToOne + @OneToMany
    # source: Mapped["MonitorSource"] = relationship(back_populates="logs")
    # 注意：如果 MonitorSource 类里没有定义 logs，这里可以单向定义
