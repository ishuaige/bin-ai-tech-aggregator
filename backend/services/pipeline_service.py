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
    """抓取 -> 落资讯主表 -> AI分析(缓存复用) -> 推送 -> 记日志 编排服务。"""

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
        logger.info("source_run_start source_id=%s type=%s value=%s", source.id, source.type, source.value)
        try:
            if source.type == "author":
                crawl_result = await self._crawler.crawl_by_author(user_name=source.value)
            elif source.type == "keyword":
                crawl_result = await self._crawler.crawl_by_keyword(keyword=source.value, query_type="Top")
            else:
                raise ValueError(f"unsupported_source_type: {source.type}")

            total_items = len(crawl_result.items)
            cleaned = self._filter.clean_items(crawl_result.items)
            enriched_items = self._scoring.attach_hotness(cleaned)

            content_map = await self._upsert_content_items(session=session, items=enriched_items)
            # 关键点：优先读 content_ai_analyses，只有缺失/文本变化才调用大模型。
            ai_insight_map = await self._build_ai_insight_map(
                session=session,
                source=source,
                items=enriched_items,
                content_map=content_map,
            )
            summary_markdown = self._build_summary_markdown(items=enriched_items, ai_insight_map=ai_insight_map)
            digest_items = self._build_digest_items(source=source, items=enriched_items, ai_insight_map=ai_insight_map)

            channels = await self._load_active_channels(session=session, source_id=source.id)
            notify_results = await self._notify.notify_channels(
                channels=channels,
                source_name=source.value,
                summary_markdown=summary_markdown,
                digest_items=digest_items,
            )
            notify_success_count = sum(1 for item in notify_results if item.success)

            status = PushStatus.SUCCESS
            if channels and notify_success_count == 0:
                status = PushStatus.FAILED

            push_log = await self._save_log(
                session=session,
                source_id=source.id,
                status=status,
                # 使用 mode='json' 把 datetime 等对象转为可序列化格式，避免 json.dumps 报错。
                raw_content=json.dumps([item.model_dump(mode="json") for item in enriched_items], ensure_ascii=False),
                ai_summary=summary_markdown,
            )
            await self._save_log_items(
                session=session,
                push_log=push_log,
                items=enriched_items,
                ai_insight_map=ai_insight_map,
            )
            await session.commit()

            logger.info(
                "source_run_done source_id=%s status=%s total_items=%s cleaned_items=%s notify_success_count=%s",
                source.id,
                status.value,
                total_items,
                len(enriched_items),
                notify_success_count,
            )
            return SourceRunResult(
                source_id=source.id,
                status=status,
                total_items=total_items,
                cleaned_items=len(enriched_items),
                notify_success_count=notify_success_count,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("source_run_failed source_id=%s", source.id)
            await self._save_log(
                session=session,
                source_id=source.id,
                status=PushStatus.FAILED,
                raw_content=None,
                ai_summary=str(exc),
            )
            await self._save_llm_call_log_entry(
                session=session,
                source_id=source.id,
                push_log_id=None,
                model="unknown",
                prompt_text="",
                response_text=None,
                status="failed",
                error_message=str(exc),
            )
            await session.commit()
            return SourceRunResult(
                source_id=source.id,
                status=PushStatus.FAILED,
                total_items=0,
                cleaned_items=0,
                notify_success_count=0,
                error=str(exc),
            )

    async def run_all_active_sources(self) -> BatchRunResult:
        async with SessionLocal() as session:
            sources = await self._load_active_sources(session=session)
            success_count = 0
            failed_count = 0
            for source in sources:
                result = await self.run_source(session=session, source=source)
                if result.status == PushStatus.SUCCESS:
                    success_count += 1
                else:
                    failed_count += 1
            logger.info(
                "batch_run_done total_sources=%s success_count=%s failed_count=%s",
                len(sources),
                success_count,
                failed_count,
            )
            return BatchRunResult(
                total_sources=len(sources),
                success_count=success_count,
                failed_count=failed_count,
            )

    async def run_source_by_id(self, source_id: int) -> SourceRunResult:
        async with SessionLocal() as session:
            source = await session.get(MonitorSource, source_id)
            if source is None:
                raise ValueError(f"source_not_found: {source_id}")
            return await self.run_source(session=session, source=source)

    async def trigger_run_now(self) -> BatchRunResult:
        """3.13 手动触发入口。"""
        return await self.run_all_active_sources()

    @staticmethod
    async def _load_active_sources(session: AsyncSession) -> list[MonitorSource]:
        stmt = select(MonitorSource).where(MonitorSource.is_active.is_(True))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def _load_active_channels(session: AsyncSession, source_id: int) -> list[PushChannel]:
        bound_total = int(
            (
                await session.execute(
                    select(func.count(SourceChannelBinding.id)).where(SourceChannelBinding.source_id == source_id)
                )
            ).scalar_one()
        )
        if bound_total > 0:
            stmt = (
                select(PushChannel)
                .join(
                    SourceChannelBinding,
                    SourceChannelBinding.channel_id == PushChannel.id,
                )
                .where(
                    SourceChannelBinding.source_id == source_id,
                    PushChannel.is_active.is_(True),
                )
            )
            rows = await session.execute(stmt)
            return list(rows.scalars().all())

        stmt = select(PushChannel).where(PushChannel.is_active.is_(True))
        rows = await session.execute(stmt)
        return list(rows.scalars().all())

    @staticmethod
    async def _save_log(
        session: AsyncSession,
        source_id: int,
        status: PushStatus,
        raw_content: str | None,
        ai_summary: str | None,
    ) -> PushLog:
        push_log = PushLog(
            source_id=source_id,
            status=status,
            raw_content=raw_content,
            ai_summary=ai_summary,
            created_at=app_now(),
        )
        session.add(push_log)
        await session.flush()
        return push_log

    @staticmethod
    async def _save_log_items(
        session: AsyncSession,
        push_log: PushLog,
        items: list[CrawlItem],
        ai_insight_map: dict[str, LLMInsightItem],
    ) -> None:
        for item in items:
            insight = ai_insight_map.get(item.tweet_id)
            score_100 = insight.ai_score if insight else PipelineService._estimate_ai_score_10(item=item) * 10
            session.add(
                PushLogItem(
                    push_log_id=push_log.id,
                    tweet_id=item.tweet_id,
                    source=item.source,
                    author_username=item.author_username or "",
                    url=item.url,
                    text=item.text,
                    hotness=item.hotness or 0,
                    ai_score=score_100,
                    created_at=app_now(),
                )
            )

    async def _build_ai_insight_map(
        self,
        session: AsyncSession,
        source: MonitorSource,
        items: list[CrawlItem],
        content_map: dict[str, ContentItem],
    ) -> dict[str, LLMInsightItem]:
        """
        为每条资讯拿到 AI 洞察：
        1) 先查表 `content_ai_analyses`
        2) 缓存不存在或原文变化时，再调用大模型
        3) 将新结果回写表，供下一次复用
        """
        result: dict[str, LLMInsightItem] = {}
        if not items:
            return result

        content_item_ids = [row.id for row in content_map.values()]
        cached_map = await self._load_ai_analysis_map(session=session, content_item_ids=content_item_ids)

        pending: list[tuple[CrawlItem, ContentItem, ContentAIAnalysis | None, str]] = []
        for item in items:
            content_item = content_map.get(item.tweet_id)
            if content_item is None:
                continue
            current_hash = self._compute_source_text_hash(item.text)
            cached = cached_map.get(content_item.id)
            if cached is not None and cached.content_hash == current_hash and cached.status == "success":
                cached_insight = LLMInsightItem(
                    tweet_id=item.tweet_id,
                    ai_score=cached.ai_score,
                    summary=cached.summary,
                    ai_title=None,
                )
                result[item.tweet_id] = cached_insight
                self._apply_ai_generated_title_if_missing(content_item=content_item, insight=cached_insight)
                continue
            pending.append((item, content_item, cached, current_hash))

        if not pending:
            return result

        batch_size = max(1, self._settings.LLM_ANALYZE_BATCH_SIZE)
        for chunk in self._chunk_items(pending, batch_size):
            batch_items = [x[0] for x in chunk]
            batch_result = await self._llm.analyze_items(batch_items)
            await self._save_llm_call_log_entry(
                session=session,
                source_id=source.id,
                push_log_id=None,
                model=batch_result.model or "unknown",
                prompt_text=batch_result.prompt_text or "",
                response_text=batch_result.raw_response_text,
                status=batch_result.status,
                error_message=batch_result.failure_reason,
            )

            insight_map = {it.tweet_id: it for it in batch_result.insights}
            for item, content_item, cached, current_hash in chunk:
                insight = insight_map.get(item.tweet_id)
                if insight is not None:
                    self._apply_ai_generated_title_if_missing(content_item=content_item, insight=insight)
                    await self._upsert_ai_analysis(
                        session=session,
                        cached=cached,
                        content_item=content_item,
                        content_hash=current_hash,
                        insight=insight,
                        model=batch_result.model or "unknown",
                        prompt_text=batch_result.prompt_text,
                        response_text=batch_result.raw_response_text,
                        status=batch_result.status,
                        failure_reason=batch_result.failure_reason,
                    )
                    result[item.tweet_id] = insight
                    continue

                fallback_insight = LLMInsightItem(
                    tweet_id=item.tweet_id,
                    ai_score=self._estimate_ai_score_10(item=item) * 10,
                    summary=self._fallback_summary(item=item),
                    ai_title=None,
                )
                await self._upsert_ai_analysis(
                    session=session,
                    cached=cached,
                    content_item=content_item,
                    content_hash=current_hash,
                    insight=fallback_insight,
                    model=batch_result.model or "unknown",
                    prompt_text=batch_result.prompt_text,
                    response_text=batch_result.raw_response_text,
                    status="failed",
                    failure_reason=batch_result.failure_reason or "missing_item_in_batch_output",
                )
                result[item.tweet_id] = fallback_insight

        return result

    @staticmethod
    def _chunk_items(
        items: list[tuple[CrawlItem, ContentItem, ContentAIAnalysis | None, str]],
        size: int,
    ) -> list[list[tuple[CrawlItem, ContentItem, ContentAIAnalysis | None, str]]]:
        return [items[idx : idx + size] for idx in range(0, len(items), size)]

    @staticmethod
    async def _load_ai_analysis_map(
        session: AsyncSession,
        content_item_ids: list[int],
    ) -> dict[int, ContentAIAnalysis]:
        if not content_item_ids:
            return {}
        stmt = select(ContentAIAnalysis).where(ContentAIAnalysis.content_item_id.in_(content_item_ids))
        rows = (await session.execute(stmt)).scalars().all()
        return {row.content_item_id: row for row in rows}

    @staticmethod
    async def _upsert_ai_analysis(
        session: AsyncSession,
        cached: ContentAIAnalysis | None,
        content_item: ContentItem,
        content_hash: str,
        insight: LLMInsightItem,
        model: str,
        prompt_text: str | None,
        response_text: str | None,
        status: str,
        failure_reason: str | None,
    ) -> None:
        if cached is None:
            session.add(
                ContentAIAnalysis(
                    content_item_id=content_item.id,
                    model=model,
                    ai_score=insight.ai_score,
                    summary=insight.summary,
                    content_hash=content_hash,
                    prompt_text=prompt_text,
                    response_text=response_text,
                    status=status,
                    failure_reason=failure_reason,
                    created_at=app_now(),
                    updated_at=app_now(),
                )
            )
            return

        cached.model = model
        cached.ai_score = insight.ai_score
        cached.summary = insight.summary
        cached.content_hash = content_hash
        cached.prompt_text = prompt_text
        cached.response_text = response_text
        cached.status = status
        cached.failure_reason = failure_reason
        cached.updated_at = app_now()

    @staticmethod
    async def _upsert_content_items(session: AsyncSession, items: list[CrawlItem]) -> dict[str, ContentItem]:
        """
        把抓取结果写入资讯主表（content_items）：
        - external_id 存第三方内容 ID（当前为 tweet_id）
        - 已存在则更新正文/热度/原始 payload
        """
        if not items:
            return {}

        external_ids = [item.tweet_id for item in items if item.tweet_id]
        stmt = select(ContentItem).where(ContentItem.platform == "twitter", ContentItem.external_id.in_(external_ids))
        existing_rows = (await session.execute(stmt)).scalars().all()
        existing_map = {row.external_id: row for row in existing_rows}

        row_map: dict[str, ContentItem] = {}
        for item in items:
            if not item.tweet_id:
                continue
            content_hash = PipelineService._compute_source_text_hash(item.text)
            raw_payload_text = json.dumps(item.raw_payload, ensure_ascii=False) if item.raw_payload else None
            row = existing_map.get(item.tweet_id)
            if row is None:
                row = ContentItem(
                    platform="twitter",
                    external_id=item.tweet_id,
                    source_type=item.source,
                    author_name=item.author_username or "",
                    url=item.url,
                    title=None,
                    content_text=item.text,
                    content_hash=content_hash,
                    published_at=to_app_tz(item.published_at),
                    raw_payload=raw_payload_text,
                    hotness=item.hotness or 0,
                    created_at=app_now(),
                    updated_at=app_now(),
                )
                session.add(row)
                await session.flush()
                existing_map[item.tweet_id] = row
            else:
                row.source_type = item.source
                row.author_name = item.author_username or ""
                row.url = item.url
                row.content_text = item.text
                row.content_hash = content_hash
                row.published_at = to_app_tz(item.published_at)
                row.raw_payload = raw_payload_text
                row.hotness = item.hotness or 0
                row.updated_at = app_now()
            row_map[item.tweet_id] = row
        return row_map

    @staticmethod
    async def _save_llm_call_log_entry(
        session: AsyncSession,
        source_id: int,
        push_log_id: int | None,
        model: str,
        prompt_text: str,
        response_text: str | None,
        status: str,
        error_message: str | None,
    ) -> None:
        session.add(
            LLMCallLog(
                source_id=source_id,
                push_log_id=push_log_id,
                model=model,
                prompt_text=prompt_text,
                response_text=response_text,
                status=status,
                error_message=error_message,
                created_at=app_now(),
            )
        )

    @staticmethod
    def _build_summary_markdown(items: list[CrawlItem], ai_insight_map: dict[str, LLMInsightItem]) -> str:
        sorted_items = sorted(items, key=lambda x: x.hotness or 0, reverse=True)
        scores = [ai_insight_map[item.tweet_id].ai_score for item in sorted_items if item.tweet_id in ai_insight_map]
        overall_score = round(sum(scores) / len(scores)) if scores else 0

        lines = [
            "## 📊 AI分析总览",
            f"- 综合评分: {overall_score}",
            f"- 数据量: {len(items)}",
            "",
            "## 🔍 关键洞察",
        ]

        for item in sorted_items[:8]:
            insight = ai_insight_map.get(item.tweet_id)
            ai_score = insight.ai_score if insight else "-"
            viewpoint = insight.summary if insight else "AI 暂未给出观点。"
            lines.append(
                f"- 来源: {item.author_username or item.source} | 热度: {item.hotness or 0} | AI评分: {ai_score} | 观点: {viewpoint}"
            )
        return "\n".join(lines)

    @staticmethod
    def _build_digest_items(
        source: MonitorSource,
        items: list[CrawlItem],
        ai_insight_map: dict[str, LLMInsightItem],
    ) -> list[DigestItem]:
        sorted_items = sorted(items, key=lambda x: x.hotness or 0, reverse=True)
        digest_items: list[DigestItem] = []

        for item in sorted_items:
            insight = ai_insight_map.get(item.tweet_id)
            ai_score_10 = PipelineService._estimate_ai_score_10(item=item)
            ai_summary_list = [PipelineService._fallback_summary(item=item)]
            if insight is not None:
                ai_score_10 = max(0, min(10, round(insight.ai_score / 10)))
                ai_summary_list = [insight.summary]

            title = item.text.strip().replace("\n", " ")
            if len(title) > 56:
                title = f"{title[:56]}..."

            publish_time = to_app_tz(item.published_at).strftime("%Y-%m-%d %H:%M") if item.published_at else "-"
            tags = [str(source.value), item.source]

            digest_items.append(
                DigestItem(
                    title=title or "未命名资讯",
                    url=item.url,
                    source=item.author_username or item.source,
                    score=ai_score_10,
                    tags=tags,
                    publish_time=publish_time,
                    ai_summary_list=ai_summary_list,
                )
            )
        return digest_items

    @staticmethod
    def _estimate_ai_score_10(item: CrawlItem) -> int:
        """
        当 LLM 未覆盖该条资讯时，使用热度和文本质量做保底分：
        - 热度占主导
        - 文本足够长时略微加分
        """
        hotness = item.hotness or 0
        base = round(hotness / 10)
        if len(item.text or "") >= 60:
            base += 1
        return max(1, min(10, base))

    @staticmethod
    def _fallback_summary(item: CrawlItem) -> str:
        text = " ".join((item.text or "").split()).strip()
        if not text:
            return "原文为空，建议人工复核。"
        if len(text) <= 48:
            return text
        return f"{text[:48]}..."

    @staticmethod
    def _compute_source_text_hash(text: str) -> str:
        normalized = " ".join((text or "").split()).strip()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _apply_ai_generated_title_if_missing(content_item: ContentItem, insight: LLMInsightItem) -> None:
        if content_item.title and content_item.title.strip():
            return

        candidate = (insight.ai_title or "").strip()
        if not candidate:
            candidate = PipelineService._build_title_from_summary(insight.summary)
        if not candidate:
            return

        if candidate.startswith("[AI生成]"):
            content_item.title = candidate[:512]
            return
        content_item.title = f"[AI生成] {candidate}"[:512]

    @staticmethod
    def _build_title_from_summary(summary: str) -> str:
        text = " ".join((summary or "").replace("\n", " ").split()).strip()
        if not text:
            return ""
        # 优先取句号前的首句，避免过长描述直接作为标题。
        for sep in ("。", "！", "？", ".", "!", "?"):
            if sep in text:
                text = text.split(sep, 1)[0].strip()
                break
        if len(text) > 28:
            text = f"{text[:28]}..."
        return text
