"""数据库异步连接与会话管理。"""

from collections.abc import AsyncGenerator

# 导入 SQLAlchemy 的异步模块
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from core import get_settings

settings = get_settings()

# 1. 创建数据库引擎 (Engine)
# Engine 是数据库连接的工厂，维护连接池 (Connection Pool)
# 类似 Java JDBC 的 DataSource
# 应用启动时创建一次 engine，后续全局复用，避免反复建连。
engine: AsyncEngine = create_async_engine(
    settings.DB_URL,
    echo=False,  # 设置为 True 会打印所有生成的 SQL 语句，开发调试很有用
    future=True, # 使用 SQLAlchemy 2.0 的新特性
)

# 2. 创建会话工厂 (SessionMaker)
# 用于生成数据库会话 (Session)
# expire_on_commit=False: 提交后不立即可用，防止异步环境下对象属性过早失效
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# 3. 定义依赖注入函数 (Dependency)
# 这是一个生成器函数 (Generator)，用于 FastAPI 的依赖注入系统
# 类似 Java Spring 的 @Autowired / @Transactional 管理的 EntityManager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖项：每个请求分配一个独立的 AsyncSession。"""
    # 创建一个新的会话
    async with SessionLocal() as session:
        try:
            # yield 把 session 交给路由函数使用
            yield session
        finally:
            # 路由函数执行完后，自动关闭会话，释放连接回连接池
            # 即使发生异常，async with 也会保证这里被执行
            await session.close()
