from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models import MonitorSource, PushChannel, SourceChannelBinding
from routers.common import ok, page
from schemas import SourceChannelBindingCreate, SourceChannelBindingResponse

router = APIRouter(prefix="/api/source-channel-bindings", tags=["source-channel-bindings"])


@router.post("")
async def create_source_channel_binding(
    payload: SourceChannelBindingCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    source = await db.get(MonitorSource, payload.source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="source_not_found")
    channel = await db.get(PushChannel, payload.channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="channel_not_found")

    row = SourceChannelBinding(source_id=payload.source_id, channel_id=payload.channel_id)
    db.add(row)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"binding_conflict:{exc.__class__.__name__}") from exc
    await db.refresh(row)
    return ok(SourceChannelBindingResponse.model_validate(row).model_dump(mode="json"))


@router.get("")
async def list_source_channel_bindings(
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    source_id: int | None = None,
    channel_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(SourceChannelBinding)
    count_stmt = select(func.count(SourceChannelBinding.id))
    if source_id is not None:
        stmt = stmt.where(SourceChannelBinding.source_id == source_id)
        count_stmt = count_stmt.where(SourceChannelBinding.source_id == source_id)
    if channel_id is not None:
        stmt = stmt.where(SourceChannelBinding.channel_id == channel_id)
        count_stmt = count_stmt.where(SourceChannelBinding.channel_id == channel_id)

    total = int((await db.execute(count_stmt)).scalar_one())
    stmt = stmt.order_by(SourceChannelBinding.id.desc()).offset((page_no - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    items = [SourceChannelBindingResponse.model_validate(row).model_dump(mode="json") for row in rows]
    return page(items=items, total=total, page_no=page_no, page_size=page_size)


@router.delete("/{binding_id}")
async def delete_source_channel_binding(binding_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    row = await db.get(SourceChannelBinding, binding_id)
    if row is None:
        return ok({"deleted": False, "reason": "binding_not_found"})
    await db.delete(row)
    await db.commit()
    return ok({"deleted": True, "id": binding_id})
