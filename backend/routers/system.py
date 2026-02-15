from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from routers.common import ok

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict:
    return ok({"status": "ok"})


@router.get("/ready")
async def ready(db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(text("SELECT 1"))
    return ok({"status": "ready"})
