from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models import ChannelPlatform, PushChannel
from routers.common import ok, page
from schemas import PushChannelCreate, PushChannelResponse, PushChannelUpdate

router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.post("")
async def create_channel(payload: PushChannelCreate, db: AsyncSession = Depends(get_db)) -> dict:
    row = PushChannel(
        platform=payload.platform.value if isinstance(payload.platform, ChannelPlatform) else str(payload.platform),
        webhook_url=str(payload.webhook_url),
        name=payload.name,
        is_active=payload.is_active,
    )
    db.add(row)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"channel_conflict:{exc.__class__.__name__}") from exc
    await db.refresh(row)
    return ok(PushChannelResponse.model_validate(row).model_dump())


@router.get("")
async def list_channels(
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    platform: ChannelPlatform | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(PushChannel)
    count_stmt = select(func.count(PushChannel.id))
    if platform is not None:
        stmt = stmt.where(PushChannel.platform == platform.value)
        count_stmt = count_stmt.where(PushChannel.platform == platform.value)
    if is_active is not None:
        stmt = stmt.where(PushChannel.is_active.is_(is_active))
        count_stmt = count_stmt.where(PushChannel.is_active.is_(is_active))

    total = int((await db.execute(count_stmt)).scalar_one())
    stmt = stmt.order_by(PushChannel.id.desc()).offset((page_no - 1) * page_size).limit(page_size)
    rows = list((await db.execute(stmt)).scalars().all())
    items = [PushChannelResponse.model_validate(row).model_dump() for row in rows]
    return page(items=items, total=total, page_no=page_no, page_size=page_size)


@router.put("/{channel_id}")
async def update_channel(channel_id: int, payload: PushChannelUpdate, db: AsyncSession = Depends(get_db)) -> dict:
    row = await db.get(PushChannel, channel_id)
    if row is None:
        raise HTTPException(status_code=404, detail="channel_not_found")

    updates = payload.model_dump(exclude_unset=True)
    if "platform" in updates and updates["platform"] is not None:
        updates["platform"] = (
            updates["platform"].value if isinstance(updates["platform"], ChannelPlatform) else str(updates["platform"])
        )
    if "webhook_url" in updates and updates["webhook_url"] is not None:
        updates["webhook_url"] = str(updates["webhook_url"])
    for key, value in updates.items():
        setattr(row, key, value)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"channel_conflict:{exc.__class__.__name__}") from exc
    await db.refresh(row)
    return ok(PushChannelResponse.model_validate(row).model_dump())


@router.delete("/{channel_id}")
async def delete_channel(channel_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    row = await db.get(PushChannel, channel_id)
    if row is None:
        return ok({"deleted": False, "reason": "channel_not_found"})
    await db.delete(row)
    await db.commit()
    return ok({"deleted": True, "id": channel_id})
