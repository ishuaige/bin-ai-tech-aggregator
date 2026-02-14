"""数据库初始化工具。"""

from db.base import Base
from db.session import engine

# 核心知识点：导入副作用 (Import Side-effects)
# 在 Python 中，类必须被“解释器执行到”才能被注册到 Base.metadata 中
# 如果不在这里导入 models，Base.metadata.create_all 就会因为找不到表定义而什么都不做
# # noqa: F401 是告诉代码检查工具（Linter）忽略“导入了但没使用”的警告
from models import MonitorSource, PushChannel, PushLog  # noqa: F401


async def init_db() -> None:
    """根据模型定义自动创建数据表（不存在才创建）。"""
    # 获取数据库连接
    async with engine.begin() as conn:
        # run_sync: 因为 create_all 是同步方法，需要在异步环境中运行
        # create_all: 类似 Hibernate 的 hbm2ddl.auto = update
        # 它会检查数据库，如果表不存在就创建，如果存在则跳过（不会修改现有表结构）
        await conn.run_sync(Base.metadata.create_all)
