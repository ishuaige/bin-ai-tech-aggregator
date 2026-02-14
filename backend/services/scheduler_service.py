from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from services.pipeline_service import PipelineService

logger = logging.getLogger(__name__)


class SchedulerService:
    """APScheduler 封装：负责注册和管理定时任务。"""

    def __init__(self, pipeline_service: PipelineService | None = None) -> None:
        self._pipeline = pipeline_service or PipelineService()
        self._scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Shanghai"))
        self._started = False

    def start(self) -> None:
        if self._started:
            return

        self._scheduler.add_job(
            self._run_daily_job,
            trigger=CronTrigger(hour=8, minute=30),
            id="daily_pipeline_job",
            replace_existing=True,
        )
        self._scheduler.start()
        self._started = True
        logger.info("scheduler_started job=daily_pipeline_job cron=08:30")

    async def shutdown(self) -> None:
        if not self._started:
            return
        self._scheduler.shutdown(wait=False)
        self._started = False
        logger.info("scheduler_shutdown")

    async def _run_daily_job(self) -> None:
        logger.info("scheduler_job_triggered job=daily_pipeline_job")
        await self._pipeline.run_all_active_sources()
