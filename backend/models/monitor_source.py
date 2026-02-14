from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


# 定义 MonitorSource 类，继承自 Base
# 这就是一个 ORM 实体，对应数据库中的一张表
class MonitorSource(Base):
    # __tablename__: 指定数据库表名 (类似 Java @Table(name="monitor_sources"))
    __tablename__ = "monitor_sources"

    # Mapped[int]: Python 的类型提示，表示这个字段映射为 Python 的 int 类型
    # mapped_column(...): 定义列的详细属性 (类似 Java @Column)
    # primary_key=True: 主键 (Java @Id)
    # autoincrement=True: 自增 (Java @GeneratedValue)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # String(20): 对应数据库 VARCHAR(20)
    # nullable=False: 必填项 (NOT NULL)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # 监控源的值（如 URL）
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Boolean: 对应数据库 BOOLEAN / TINYINT
    # default=True: 默认值为 True
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Mapped[str | None]: 表示这个字段可能是字符串，也可能是 None (Java 的 null)
    # nullable=True: 允许数据库存 NULL
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
