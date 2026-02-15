from __future__ import annotations

from datetime import datetime, time

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import app_now
from db.session import get_db
from models import PushLog, PushLogItem, PushStatus
from routers.common import ok

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview")
async def overview(db: AsyncSession = Depends(get_db)) -> dict:
    now = app_now()
    today_start = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)

    total_runs_today = int(
        (await db.execute(select(func.count(PushLog.id)).where(PushLog.created_at >= today_start))).scalar_one()
    )
    success_runs_today = int(
        (
            await db.execute(
                select(func.count(PushLog.id)).where(
                    PushLog.created_at >= today_start,
                    PushLog.status == PushStatus.SUCCESS.value,
                )
            )
        ).scalar_one()
    )
    items_today = int(
        (
            await db.execute(
                select(func.count(PushLogItem.id))
                .join(PushLog, PushLog.id == PushLogItem.push_log_id)
                .where(PushLog.created_at >= today_start)
            )
        ).scalar_one()
    )
    latest_log = (
        (
            await db.execute(
                select(PushLog).order_by(PushLog.created_at.desc()).limit(1)
            )
        )
        .scalars()
        .first()
    )
    latest_status = latest_log.status.value if latest_log else "none"
    llm_tokens_estimate = items_today * 700

    return ok(
        {
            "today_fetch_count": items_today,
            "today_run_count": total_runs_today,
            "today_success_count": success_runs_today,
            "latest_run_status": latest_status,
            "latest_run_at": latest_log.created_at.isoformat() if latest_log else None,
            "token_estimate": llm_tokens_estimate,
        }
    )
