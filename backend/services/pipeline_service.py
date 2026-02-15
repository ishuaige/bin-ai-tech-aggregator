from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import app_now, get_settings, to_app_tz
from db.session import SessionLocal
from models import (
    ContentAIAnalysis,
    ContentItem,
    LLMCallLog,
    MonitorSource,
    PushChannel,
    PushLog,
    PushLogItem,
    PushStatus,
    SourceChannelBinding,
)
from schemas import CrawlItem, LLMInsightItem
from services.content_filter_service import ContentFilterService
from services.crawler_service import CrawlerService
from services.llm_service import LLMService
from services.notify_service import DigestItem, NotifyService
from services.scoring_service import ScoringService

logger = logging.getLogger(__name__)


@dataclass
class SourceRunResult:
    """单次运行结果的数据类 (Data Class)。
    
    @dataclass 自动生成 __init__, __repr__, __eq__ 等方法。
    类似 Java 的 Lombok @Data。
    """
    source_id: int
    status: PushStatus
    total_items: int
    cleaned_items: int
    notify_success_count: int
    error: str | None = None


@dataclass
class BatchRunResult:
    total_sources: int
    success_count: int
    failed_count: int


class PipelineService:
    """核心编排服务 (Orchestrator)。
    
    负责将各个原子服务串联起来：
    抓取 -> 清洗 -> 评分 -> 落库 -> AI分析 -> 推送 -> 记录日志
    """

    def __init__(
        self,
        crawler_service: CrawlerService | None = None,
        filter_service: ContentFilterService | None = None,
        llm_service: LLMService | None = None,
        notify_service: NotifyService | None = None,
        scoring_service: ScoringService | None = None,
    ) -> None:
        self._settings = get_settings()
        self._crawler = crawler_service or CrawlerService()
        self._filter = filter_service or ContentFilterService()
        self._llm = llm_service or LLMService()
        self._notify = notify_service or NotifyService()
        self._scoring = scoring_service or ScoringService()

    async def run_source(self, session: AsyncSession, source: MonitorSource) -> SourceRunResult:
        """
        处理单个监控源的全流程。
        
        Args:
            session: 数据库会话
            source: 监控源配置对象
        """
        logger.info("source_run_start source_id=%s type=%s value=%s", source.id, source.type, source.value)
        try:
            # 1. 抓取 (Crawl)
            if source.type == "author":
                crawl_result = await self._crawler.crawl_by_author(user_name=source.value)
            elif source.type == "keyword":
                crawl_result = await self._crawler.crawl_by_keyword(keyword=source.value, query_type="Top")
            else:
                raise ValueError(f"unsupported_source_type: {source.type}")

            total_items = len(crawl_result.items)
            
            # 2. 清洗 (Filter)
            cleaned = self._filter.clean_items(crawl_result.items)
            
            # 3. 评分 (Score)
            enriched_items = self._scoring.attach_hotness(cleaned)

            # 4. 落库 (Persist)
            # 这一步很重要：先把内容存下来，防止后续步骤失败导致数据丢失
            content_map = await self._upsert_content_items(session=session, items=enriched_items)
            
            # 5. AI 分析 (Analyze)
            # 关键点：优先读 content_ai_analyses 表，只有缺失/文本变化才真正调用大模型
            # 这是一个典型的“缓存优先”策略
            ai_insight_map = await self._build_ai_insight_map(
                session=session,
                source=source,
                items=enriched_items,
                content_map=content_map,
            )
            
            # 6. 生成报告 (Summarize)
            summary_markdown = self._build_summary_markdown(items=enriched_items, ai_insight_map=ai_insight_map)
            digest_items = self._build_digest_items(source=source, items=enriched_items, ai_insight_map=ai_insight_map)

            # 7. 推送 (Notify)
            channels = await self._load_active_channels(session=session, source_id=source.id)
            notify_results = await self._notify.notify_channels(
                channels=channels,
                source_name=source.value,
                summary_markdown=summary_markdown,
                digest_items=digest_items,
            )
            
            # TODO: 记录 PushLog (省略了代码)
            
            return SourceRunResult(
                source_id=source.id,
                status=PushStatus.SUCCESS,
                total_items=total_items,
                cleaned_items=len(cleaned),
                notify_success_count=len([r for r in notify_results if r]),
            )
            
        except Exception as e:
            logger.error("source_run_failed source_id=%s error=%s", source.id, e, exc_info=True)
            return SourceRunResult(
                source_id=source.id,
                status=PushStatus.FAILED,
                total_items=0,
                cleaned_items=0,
                notify_success_count=0,
                error=str(e),
            )

    # --- 以下是私有辅助方法，仅保留签名 ---
    
    async def _upsert_content_items(self, session: AsyncSession, items: list[CrawlItem]) -> dict[str, ContentItem]:
        """Insert or Update 内容表。"""
        return {}

    async def _build_ai_insight_map(self, session: AsyncSession, source: MonitorSource, items: list[CrawlItem], content_map: dict[str, ContentItem]) -> dict[str, LLMInsightItem]:
        return {}

    def _build_summary_markdown(self, items: list[CrawlItem], ai_insight_map: dict[str, LLMInsightItem]) -> str:
        return ""

    def _build_digest_items(self, source: MonitorSource, items: list[CrawlItem], ai_insight_map: dict[str, LLMInsightItem]) -> list[DigestItem]:
        return []

    async def _load_active_channels(self, session: AsyncSession, source_id: int) -> list[PushChannel]:
        return []
