"""本地开发/测试用的初始化数据脚本（可重复执行）。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import ChannelPlatform, MonitorSource, PushChannel, PushLog, PushStatus, SourceType


async def _seed_sources(session: AsyncSession) -> dict[str, MonitorSource]:
    seed_sources = [
        {
            "type": SourceType.AUTHOR,
            "value": "karpathy",
            "remark": "seed: author source",
            "is_active": True,
        },
        {
            "type": SourceType.KEYWORD,
            "value": "FastAPI",
            "remark": "seed: keyword source",
            "is_active": True,
        },
    ]
    source_map: dict[str, MonitorSource] = {}
    for payload in seed_sources:
        # 幂等策略：用 (type, value) 作为“业务唯一键”查重。
        stmt = select(MonitorSource).where(
            MonitorSource.type == payload["type"],
            MonitorSource.value == payload["value"],
        )
        result = await session.execute(stmt)
        source = result.scalar_one_or_none()
        if source is None:
            source = MonitorSource(**payload)
            session.add(source)
            await session.flush()
        source_map[str(payload["value"])] = source
    return source_map


async def _seed_channels(session: AsyncSession) -> None:
    seed_channels = [
        {
            "platform": ChannelPlatform.WECHAT,
            "webhook_url": "https://example.com/webhook/wechat-ai-daily",
            "name": "AI 核心前沿群",
            "is_active": True,
        },
        {
            "platform": ChannelPlatform.FEISHU,
            "webhook_url": "https://example.com/webhook/feishu-frontend",
            "name": "前端技术早报群",
            "is_active": True,
        },
    ]
    for payload in seed_channels:
        # 幂等策略：按渠道名称查重，避免重复插入。
        stmt = select(PushChannel).where(PushChannel.name == payload["name"])
        result = await session.execute(stmt)
        channel = result.scalar_one_or_none()
        if channel is None:
            session.add(PushChannel(**payload))


async def _seed_logs(session: AsyncSession, source_map: dict[str, MonitorSource]) -> None:
    seed_logs = [
        {
            "source_key": "karpathy",
            "raw_content": "Tweet: A short post about model reasoning improvements.",
            "ai_summary": "- **核心点**: 模型推理质量持续提升。",
            "status": PushStatus.SUCCESS,
        },
        {
            "source_key": "FastAPI",
            "raw_content": "Tweet: FastAPI released a new async feature update.",
            "ai_summary": "- **核心点**: FastAPI 异步能力增强。",
            "status": PushStatus.SUCCESS,
        },
    ]
    for payload in seed_logs:
        source = source_map[payload["source_key"]]
        # 幂等策略：同一个 source + 同一段原文，只保留一条日志。
        stmt = select(PushLog).where(
            PushLog.source_id == source.id,
            PushLog.raw_content == payload["raw_content"],
        )
        result = await session.execute(stmt)
        log = result.scalar_one_or_none()
        if log is None:
            session.add(
                PushLog(
                    source_id=source.id,
                    raw_content=payload["raw_content"],
                    ai_summary=payload["ai_summary"],
                    status=payload["status"],
                )
            )


async def seed_db(session: AsyncSession) -> None:
    """写入演示数据，重复执行不会产生脏重复数据。"""
    source_map = await _seed_sources(session)
    await _seed_channels(session)
    await _seed_logs(session, source_map)
    await session.commit()
