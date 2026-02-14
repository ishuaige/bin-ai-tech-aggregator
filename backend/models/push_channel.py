from sqlalchemy import Boolean, CheckConstraint, Enum, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from models.enums import ChannelPlatform


class PushChannel(Base):
    """推送渠道表：保存企业微信/飞书/钉钉等 webhook 配置。"""

    __tablename__ = "push_channels"
    
    # __table_args__: 定义表级别的约束（索引、唯一键、检查约束）
    __table_args__ = (
        # 唯一约束 (Unique Constraint): name 字段必须唯一
        UniqueConstraint("name", name="uq_push_channels_name"),
        # 唯一约束: webhook_url 必须唯一
        UniqueConstraint("webhook_url", name="uq_push_channels_webhook_url"),
        # 检查约束 (Check Constraint): platform 字段只能是指定的值
        CheckConstraint(
            "platform in ('wechat', 'dingtalk', 'feishu')",
            name="ck_push_channels_platform",
        ),
        # 索引 (Index): 加速查询
        Index("idx_push_channels_platform", "platform"),
        Index("idx_push_channels_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 枚举类型映射 (Enum)
    # ChannelPlatform 是 Python 的 Enum 类
    platform: Mapped[ChannelPlatform] = mapped_column(
        Enum(
            ChannelPlatform,
            name="channel_platform", # 数据库中的枚举类型名称
            native_enum=False,       # False 表示用 VARCHAR 存储，兼容性更好
            # values_callable: 告诉 SQLAlchemy 如何获取枚举的值存入数据库
            # 这里取枚举的 .value 属性（即 'wechat' 等小写字符串）
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    
    webhook_url: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
