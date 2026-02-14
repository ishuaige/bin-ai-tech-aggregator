from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

# 导入配置加载函数
from core import get_settings


# @asynccontextmanager 是 Python 的上下文管理器装饰器
# 这里用于定义应用的生命周期（启动前做什么，关闭后做什么）
# 类似 Java Spring Boot 的 @PostConstruct 和 @PreDestroy
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # --- 启动阶段 (Startup) ---
    # 在应用启动时，先加载并校验配置
    # 如果 .env 文件缺少必要的配置，这里会直接报错停止启动，避免运行时出错
    get_settings()
    
    yield  # 这里的 yield 是分界线，上面是启动代码，下面是关闭代码
    
    # --- 关闭阶段 (Shutdown) ---
    # 如果有数据库连接池关闭、Redis 断开等操作，写在这里
    pass

# 初始化 FastAPI 应用
# lifespan 参数指定了上面的生命周期管理器
app = FastAPI(lifespan=lifespan)


# 定义一个 GET 请求接口
# 访问路径: http://localhost:8000/health
# async def: 定义异步函数，FastAPI 推荐用法，性能更高
# -> dict[str, str]: 类型提示，告诉开发者和 IDE 返回值是一个 Map<String, String>
@app.get("/health")
async def health() -> dict[str, str]:
    # Python 字典字面量，等同于 Java 的 Map.of("status", "ok")
    return {"status": "ok"}
