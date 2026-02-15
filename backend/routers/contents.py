from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import app_now
from db.session import get_db
from models import ContentAIAnalysis, ContentItem, LLMCallLog, PushLog, PushLogItem
from routers.common import ok, page
from schemas import CrawlItem, LLMInsightItem
from schemas.content import ContentAnalysisInfo, ContentListItem
from services.llm_service import LLMService

router = APIRouter(prefix="/api/contents", tags=["contents"])
_llm_service = LLMService()


@router.get("")
async def list_contents(
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = None,
    platform: str | None = None,
    ai_status: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    conditions = []
    if keyword:
        like = f"%{keyword.strip()}%"
        conditions.append(
            or_(
                ContentItem.title.like(like),
                ContentItem.content_text.like(like),
                ContentItem.author_name.like(like),
                ContentAIAnalysis.summary.like(like),
            )
        )
    if platform:
        conditions.append(ContentItem.platform == platform.strip())
    if ai_status:
        conditions.append(ContentAIAnalysis.status == ai_status.strip())

    stmt = select(ContentItem, ContentAIAnalysis).outerjoin(
        ContentAIAnalysis,
        ContentAIAnalysis.content_item_id == ContentItem.id,
    )
    count_stmt = select(func.count(ContentItem.id)).select_from(ContentItem).outerjoin(
        ContentAIAnalysis,
        ContentAIAnalysis.content_item_id == ContentItem.id,
    )
    if conditions:
        where_clause = and_(*conditions)
        stmt = stmt.where(where_clause)
        count_stmt = count_stmt.where(where_clause)

    total = int((await db.execute(count_stmt)).scalar_one())
    stmt = stmt.order_by(ContentItem.published_at.desc(), ContentItem.id.desc()).offset((page_no - 1) * page_size).limit(
        page_size
    )
    rows = (await db.execute(stmt)).all()

    items = [_serialize_content_item(content_item=content_item, analysis=analysis) for content_item, analysis in rows]

    return page(items=items, total=total, page_no=page_no, page_size=page_size)


@router.post("/{content_id}/analyze")
async def analyze_content(content_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    content_item = await db.get(ContentItem, content_id)
    if content_item is None:
        raise HTTPException(status_code=404, detail="content_not_found")

    crawl_item = CrawlItem(
        source=content_item.source_type,
        tweet_id=content_item.external_id,
        author_username=content_item.author_name or "",
        url=content_item.url,
        text=content_item.content_text,
        published_at=content_item.published_at,
        hotness=content_item.hotness,
        raw_payload={},
    )

    batch_result = await _llm_service.analyze_items([crawl_item])
    insight_map = {insight.tweet_id: insight for insight in batch_result.insights}
    insight = insight_map.get(content_item.external_id)
    if insight is None:
        insight = _build_fallback_insight(crawl_item=crawl_item)
        status = "failed"
        failure_reason = batch_result.failure_reason or "missing_item_in_batch_output"
    else:
        status = batch_result.status
        failure_reason = batch_result.failure_reason

    analysis_row = (
        (
            await db.execute(
                select(ContentAIAnalysis).where(
                    ContentAIAnalysis.content_item_id == content_item.id,
                )
            )
        )
        .scalars()
        .first()
    )
    content_hash = _compute_source_text_hash(content_item.content_text)
    now = app_now()

    if analysis_row is None:
        analysis_row = ContentAIAnalysis(
            content_item_id=content_item.id,
            model=batch_result.model or "unknown",
            ai_score=insight.ai_score,
            summary=insight.summary,
            content_hash=content_hash,
            prompt_text=batch_result.prompt_text,
            response_text=batch_result.raw_response_text,
            status=status,
            failure_reason=failure_reason,
            created_at=now,
            updated_at=now,
        )
        db.add(analysis_row)
    else:
        analysis_row.model = batch_result.model or "unknown"
        analysis_row.ai_score = insight.ai_score
        analysis_row.summary = insight.summary
        analysis_row.content_hash = content_hash
        analysis_row.prompt_text = batch_result.prompt_text
        analysis_row.response_text = batch_result.raw_response_text
        analysis_row.status = status
        analysis_row.failure_reason = failure_reason
        analysis_row.updated_at = now

    _apply_ai_generated_title_if_missing(content_item=content_item, insight=insight)
    source_id = await _resolve_source_id_for_content(db=db, content_item=content_item)
    if source_id is not None:
        db.add(
            LLMCallLog(
                source_id=source_id,
                push_log_id=None,
                model=batch_result.model or "unknown",
                prompt_text=batch_result.prompt_text or "",
                response_text=batch_result.raw_response_text,
                status=status,
                error_message=failure_reason,
                created_at=now,
            )
        )
    content_item.updated_at = now
    await db.commit()
    await db.refresh(content_item)
    await db.refresh(analysis_row)

    return ok(_serialize_content_item(content_item=content_item, analysis=analysis_row))


def _serialize_content_item(content_item: ContentItem, analysis: ContentAIAnalysis | None) -> dict:
    ai_data = None
    if analysis is not None:
        ai_data = ContentAnalysisInfo(
            status=analysis.status,
            ai_score=analysis.ai_score,
            summary=analysis.summary,
            model=analysis.model,
            updated_at=analysis.updated_at,
            failure_reason=analysis.failure_reason,
        ).model_dump(mode="json")

    return ContentListItem(
        id=content_item.id,
        platform=content_item.platform,
        source_type=content_item.source_type,
        external_id=content_item.external_id,
        author_name=content_item.author_name,
        url=content_item.url,
        title=content_item.title,
        content_text=content_item.content_text,
        hotness=content_item.hotness,
        published_at=content_item.published_at,
        created_at=content_item.created_at,
        ai=ai_data,
    ).model_dump(mode="json")


def _build_fallback_insight(crawl_item: CrawlItem) -> LLMInsightItem:
    hotness = crawl_item.hotness or 0
    score = max(10, min(100, round(hotness)))
    summary = " ".join((crawl_item.text or "").split()).strip()
    if not summary:
        summary = "原文为空，建议人工复核。"
    if len(summary) > 120:
        summary = f"{summary[:120]}..."
    return LLMInsightItem(
        tweet_id=crawl_item.tweet_id,
        ai_score=score,
        summary=summary,
        ai_title=None,
    )


def _apply_ai_generated_title_if_missing(content_item: ContentItem, insight: LLMInsightItem) -> None:
    if content_item.title and content_item.title.strip():
        return

    candidate = (insight.ai_title or "").strip()
    if not candidate:
        candidate = _build_title_from_summary(insight.summary)
    if not candidate:
        return
    content_item.title = f"[AI生成] {candidate}"[:512]


def _build_title_from_summary(summary: str) -> str:
    text = " ".join((summary or "").replace("\n", " ").split()).strip()
    if not text:
        return ""
    for sep in ("。", "！", "？", ".", "!", "?"):
        if sep in text:
            text = text.split(sep, 1)[0].strip()
            break
    if len(text) > 28:
        text = f"{text[:28]}..."
    return text


def _compute_source_text_hash(text: str) -> str:
    normalized = " ".join((text or "").split()).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def _resolve_source_id_for_content(db: AsyncSession, content_item: ContentItem) -> int | None:
    stmt = (
        select(PushLog.source_id)
        .select_from(PushLogItem)
        .join(PushLog, PushLog.id == PushLogItem.push_log_id)
        .where(PushLogItem.tweet_id == content_item.external_id)
        .order_by(PushLog.created_at.desc())
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        return None
    return int(row[0])
