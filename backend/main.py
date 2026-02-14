from contextlib import asynccontextmanager
import logging
import uuid
from typing import AsyncIterator

from fastapi import FastAPI
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# 导入配置加载函数
from core import get_settings, setup_logging
from core.request_context import request_id_ctx_var
from db.init_db import init_db
from db.session import SessionLocal
from models import PushChannel
from services import NotifyService, PipelineService, SchedulerService

logger = logging.getLogger(__name__)

pipeline_service = PipelineService()
scheduler_service = SchedulerService(pipeline_service=pipeline_service)
notify_service = NotifyService()


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        token = request_id_ctx_var.set(request_id)
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            return response
        finally:
            request_id_ctx_var.reset(token)


async def validate_no_duplicate_webhooks() -> None:
    """
    启动校验：禁止重复 webhook_url。
    说明：历史库可能在早期无唯一约束，导致重复配置，需要显式拦截。
    """
    async with SessionLocal() as session:
        stmt = (
            select(PushChannel.webhook_url, func.count(PushChannel.id))
            .group_by(PushChannel.webhook_url)
            .having(func.count(PushChannel.id) > 1)
        )
        rows = (await session.execute(stmt)).all()

    if rows:
        duplicated = [str(row[0]) for row in rows if row[0]]
        logger.error("duplicate_webhook_detected count=%s urls=%s", len(duplicated), duplicated[:5])
        raise RuntimeError("检测到重复 webhook_url 配置，请先去重后再启动服务。")


class WebhookTestRequest(BaseModel):
    channel_id: int = Field(description="push_channels 表中的渠道 ID")
    source_name: str = Field(default="manual-test", description="消息里展示的来源名称")
    summary_markdown: str = Field(
        default="- 这是一条手动触发的渠道测试消息。",
        description="要发送的 Markdown 内容",
    )


# @asynccontextmanager 是 Python 的上下文管理器装饰器
# 这里用于定义应用的生命周期（启动前做什么，关闭后做什么）
# 类似 Java Spring Boot 的 @PostConstruct 和 @PreDestroy
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # --- 启动阶段 (Startup) ---
    # 在应用启动时，先加载并校验配置
    # 如果 .env 文件缺少必要的配置，这里会直接报错停止启动，避免运行时出错
    setup_logging()
    get_settings()
    await init_db()
    await validate_no_duplicate_webhooks()
    scheduler_service.start()
    logger.info("application_started")
    
    yield  # 这里的 yield 是分界线，上面是启动代码，下面是关闭代码
    
    # --- 关闭阶段 (Shutdown) ---
    # 如果有数据库连接池关闭、Redis 断开等操作，写在这里
    await scheduler_service.shutdown()
    logger.info("application_shutdown")

# 初始化 FastAPI 应用
# lifespan 参数指定了上面的生命周期管理器
app = FastAPI(lifespan=lifespan)
app.add_middleware(RequestIdMiddleware)


# 定义一个 GET 请求接口
# 访问路径: http://localhost:8000/health
# async def: 定义异步函数，FastAPI 推荐用法，性能更高
# -> dict[str, str]: 类型提示，告诉开发者和 IDE 返回值是一个 Map<String, String>
@app.get("/health")
async def health() -> dict[str, str]:
    # Python 字典字面量，等同于 Java 的 Map.of("status", "ok")
    return {"status": "ok"}


@app.post("/internal/jobs/run-now")
async def run_now() -> dict[str, int]:
    """3.13 手动触发入口（内部调试接口）。"""
    result = await pipeline_service.trigger_run_now()
    return {
        "total_sources": result.total_sources,
        "success_count": result.success_count,
        "failed_count": result.failed_count,
    }


@app.post("/internal/webhook/test")
async def webhook_test(req: WebhookTestRequest) -> dict:
    """只测试某个渠道的 webhook 发送，不依赖抓取和 LLM。"""
    async with SessionLocal() as session:
        stmt = select(PushChannel).where(PushChannel.id == req.channel_id)
        result = await session.execute(stmt)
        channel = result.scalar_one_or_none()

    if channel is None:
        return {"ok": False, "error": f"channel_not_found:{req.channel_id}"}
    if not channel.is_active:
        return {"ok": False, "error": f"channel_inactive:{req.channel_id}"}

    notify_results = await notify_service.notify_channels(
        channels=[channel],
        source_name=req.source_name,
        summary_markdown=req.summary_markdown,
    )
    first = notify_results[0] if notify_results else None
    return {
        "ok": bool(first and first.success),
        "channel_id": req.channel_id,
        "channel_name": channel.name,
        "status_code": first.status_code if first else None,
        "error": first.error if first else "unknown_send_error",
    }
