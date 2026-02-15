from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models import PushLog, PushStatus
from routers.common import ok, page
from schemas import PushLogDetail, PushLogListItem

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
async def list_logs(
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: PushStatus | None = None,
    source_id: int | None = None,
    keyword: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    conditions = []
    if status is not None:
        conditions.append(PushLog.status == status.value)
    if source_id is not None:
        conditions.append(PushLog.source_id == source_id)
    if keyword:
        like = f"%{keyword.strip()}%"
        conditions.append(or_(PushLog.ai_summary.like(like), PushLog.raw_content.like(like)))
    if date_from is not None:
        conditions.append(PushLog.created_at >= date_from)
    if date_to is not None:
        conditions.append(PushLog.created_at <= date_to)

    stmt = select(PushLog)
    count_stmt = select(func.count(PushLog.id))
    if conditions:
        where_clause = and_(*conditions)
        stmt = stmt.where(where_clause)
        count_stmt = count_stmt.where(where_clause)

    total = int((await db.execute(count_stmt)).scalar_one())
    stmt = stmt.order_by(PushLog.id.desc()).offset((page_no - 1) * page_size).limit(page_size)
    rows = list((await db.execute(stmt)).scalars().all())
    items = [PushLogListItem.model_validate(row).model_dump(mode="json") for row in rows]
    return page(items=items, total=total, page_no=page_no, page_size=page_size)


@router.get("/{log_id}")
async def get_log_detail(log_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    row = await db.get(PushLog, log_id)
    if row is None:
        raise HTTPException(status_code=404, detail="log_not_found")
    return ok(PushLogDetail.model_validate(row).model_dump(mode="json"))
