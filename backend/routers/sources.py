from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models import MonitorSource, PushLog, SourceType
from routers.common import ok, page
from schemas import MonitorSourceCreate, MonitorSourceResponse, MonitorSourceUpdate

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.post("")
async def create_source(payload: MonitorSourceCreate, db: AsyncSession = Depends(get_db)) -> dict:
    row = MonitorSource(
        type=payload.type.value if isinstance(payload.type, SourceType) else str(payload.type),
        value=payload.value,
        is_active=payload.is_active,
        remark=payload.remark,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ok(MonitorSourceResponse.model_validate(row).model_dump())


@router.get("")
async def list_sources(
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    type: SourceType | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(MonitorSource)
    count_stmt = select(func.count(MonitorSource.id))
    if type is not None:
        stmt = stmt.where(MonitorSource.type == type.value)
        count_stmt = count_stmt.where(MonitorSource.type == type.value)
    if is_active is not None:
        stmt = stmt.where(MonitorSource.is_active.is_(is_active))
        count_stmt = count_stmt.where(MonitorSource.is_active.is_(is_active))

    total = int((await db.execute(count_stmt)).scalar_one())
    stmt = stmt.order_by(MonitorSource.id.desc()).offset((page_no - 1) * page_size).limit(page_size)
    rows = list((await db.execute(stmt)).scalars().all())
    items = [MonitorSourceResponse.model_validate(row).model_dump() for row in rows]
    return page(items=items, total=total, page_no=page_no, page_size=page_size)


@router.put("/{source_id}")
async def update_source(source_id: int, payload: MonitorSourceUpdate, db: AsyncSession = Depends(get_db)) -> dict:
    row = await db.get(MonitorSource, source_id)
    if row is None:
        raise HTTPException(status_code=404, detail="source_not_found")

    updates = payload.model_dump(exclude_unset=True)
    if "type" in updates and updates["type"] is not None:
        updates["type"] = updates["type"].value if isinstance(updates["type"], SourceType) else str(updates["type"])
    for key, value in updates.items():
        setattr(row, key, value)

    await db.commit()
    await db.refresh(row)
    return ok(MonitorSourceResponse.model_validate(row).model_dump())


@router.delete("/{source_id}")
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    row = await db.get(MonitorSource, source_id)
    if row is None:
        return ok({"deleted": False, "reason": "source_not_found"})

    log_count = int((await db.execute(select(func.count(PushLog.id)).where(PushLog.source_id == source_id))).scalar_one())
    if log_count > 0:
        raise HTTPException(status_code=409, detail="source_has_logs_cannot_delete")

    await db.delete(row)
    await db.commit()
    return ok({"deleted": True, "id": source_id})
