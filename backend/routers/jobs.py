from __future__ import annotations

import asyncio
import logging
import time
import uuid

from fastapi import APIRouter

from routers.common import ok
from services import PipelineService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])

_pipeline_service = PipelineService()
_job_state: dict[str, dict] = {}
_JOB_STATE_MAX_SIZE = 500
_JOB_STATE_TTL_SECONDS = 24 * 3600


def _cleanup_job_state() -> None:
    now = time.time()
    expired_ids = []
    for job_id, state in _job_state.items():
        updated_at = float(state.get("updated_at", now))
        if now - updated_at > _JOB_STATE_TTL_SECONDS:
            expired_ids.append(job_id)

    for job_id in expired_ids:
        _job_state.pop(job_id, None)

    if len(_job_state) <= _JOB_STATE_MAX_SIZE:
        return
    overflow = len(_job_state) - _JOB_STATE_MAX_SIZE
    oldest_ids = sorted(_job_state.keys(), key=lambda key: float(_job_state[key].get("updated_at", now)))[:overflow]
    for job_id in oldest_ids:
        _job_state.pop(job_id, None)


async def _run_job(job_id: str) -> None:
    try:
        result = await _pipeline_service.trigger_run_now()
        _job_state[job_id] = {
            "status": "done",
            "updated_at": time.time(),
            "result": {
                "total_sources": result.total_sources,
                "success_count": result.success_count,
                "failed_count": result.failed_count,
            },
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("run_now_job_failed job_id=%s", job_id)
        _job_state[job_id] = {"status": "failed", "error": str(exc), "updated_at": time.time()}
    finally:
        _cleanup_job_state()


@router.post("/run-now")
async def run_now() -> dict:
    _cleanup_job_state()
    job_id = str(uuid.uuid4())
    _job_state[job_id] = {"status": "running", "updated_at": time.time()}
    asyncio.create_task(_run_job(job_id))
    return ok({"job_id": job_id, "status": "accepted"}, message="accepted")


@router.get("/run-now/{job_id}")
async def run_now_status(job_id: str) -> dict:
    _cleanup_job_state()
    state = _job_state.get(job_id)
    if state is None:
        return ok({"job_id": job_id, "status": "not_found"})
    return ok({"job_id": job_id, **state})
