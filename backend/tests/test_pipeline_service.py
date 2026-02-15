import pytest

from models import MonitorSource, PushStatus
from schemas import CrawlBatchResult, CrawlItem, LLMInsightItem
from services.pipeline_service import PipelineService


class _FakeCrawler:
    async def crawl_by_author(self, user_name: str, cursor: str | None = None) -> CrawlBatchResult:
        return CrawlBatchResult(
            items=[
                CrawlItem(
                    source="author_timeline",
                    tweet_id="1",
                    author_username=user_name,
                    url="https://x.com/a/status/1",
                    text="FastAPI release",
                    published_at=None,
                )
            ]
        )

    async def crawl_by_keyword(self, keyword: str, query_type: str = "Latest", cursor: str | None = None) -> CrawlBatchResult:
        return CrawlBatchResult(items=[])


class _FakeFilter:
    def clean_items(self, items: list[CrawlItem]) -> list[CrawlItem]:
        return items


class _FakeLLM:
    async def analyze_item(self, item: CrawlItem):
        return None


class _FakeNotify:
    async def notify_channels(self, channels, source_name: str, summary_markdown: str, digest_items=None):
        return []


class _FakeSession:
    def add(self, _obj) -> None:
        return None

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None


@pytest.mark.asyncio
async def test_run_source_success(monkeypatch: pytest.MonkeyPatch) -> None:
    service = PipelineService(
        crawler_service=_FakeCrawler(),
        filter_service=_FakeFilter(),
        llm_service=_FakeLLM(),
        notify_service=_FakeNotify(),
    )

    async def _no_channels(session, source_id):
        return []

    class _FakePushLog:
        id = 1

    async def _no_save(**kwargs):
        return _FakePushLog()

    async def _no_save_items(**kwargs):
        return None

    async def _no_ai_map(*args, **kwargs):
        return {"1": LLMInsightItem(tweet_id="1", ai_score=80, summary="test")}

    async def _no_upsert_content_items(*args, **kwargs):
        class _Content:
            id = 1

        return {"1": _Content()}

    monkeypatch.setattr(PipelineService, "_load_active_channels", staticmethod(_no_channels))
    monkeypatch.setattr(PipelineService, "_save_log", staticmethod(_no_save))
    monkeypatch.setattr(PipelineService, "_save_log_items", staticmethod(_no_save_items))
    monkeypatch.setattr(PipelineService, "_upsert_content_items", staticmethod(_no_upsert_content_items))
    monkeypatch.setattr(PipelineService, "_build_ai_insight_map", _no_ai_map)

    source = MonitorSource(id=1, type="author", value="karpathy", is_active=True, remark=None)
    result = await service.run_source(session=_FakeSession(), source=source)
    assert result.status == PushStatus.SUCCESS
    assert result.total_items == 1


@pytest.mark.asyncio
async def test_run_source_failed_when_type_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    service = PipelineService(
        crawler_service=_FakeCrawler(),
        filter_service=_FakeFilter(),
        llm_service=_FakeLLM(),
        notify_service=_FakeNotify(),
    )

    async def _no_channels(session, source_id):
        return []

    class _FakePushLog:
        id = 1

    async def _no_save(**kwargs):
        return _FakePushLog()

    async def _no_save_items(**kwargs):
        return None

    async def _no_ai_map(*args, **kwargs):
        return {}

    async def _no_upsert_content_items(*args, **kwargs):
        return {}

    monkeypatch.setattr(PipelineService, "_load_active_channels", staticmethod(_no_channels))
    monkeypatch.setattr(PipelineService, "_save_log", staticmethod(_no_save))
    monkeypatch.setattr(PipelineService, "_save_log_items", staticmethod(_no_save_items))
    monkeypatch.setattr(PipelineService, "_upsert_content_items", staticmethod(_no_upsert_content_items))
    monkeypatch.setattr(PipelineService, "_build_ai_insight_map", _no_ai_map)

    source = MonitorSource(id=2, type="unknown", value="x", is_active=True, remark=None)
    result = await service.run_source(session=_FakeSession(), source=source)
    assert result.status == PushStatus.FAILED


def test_fallback_score_and_summary_when_llm_missing() -> None:
    item = CrawlItem(
        source="author_timeline",
        tweet_id="x1",
        author_username="alice",
        url="https://x.com/a/status/1",
        text="This is a long enough text for fallback summary generation in pipeline.",
        published_at=None,
        hotness=34,
    )
    score = PipelineService._estimate_ai_score_10(item)
    summary = PipelineService._fallback_summary(item)
    assert 1 <= score <= 10
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_apply_ai_generated_title_if_missing() -> None:
    class _Content:
        title = None

    content = _Content()
    insight = LLMInsightItem(
        tweet_id="x2",
        ai_score=86,
        summary="这条资讯指出新模型在函数调用稳定性上有明显改进，适合生产环境。",
        ai_title="函数调用稳定性明显改进",
    )
    PipelineService._apply_ai_generated_title_if_missing(content_item=content, insight=insight)  # type: ignore[arg-type]
    assert content.title == "[AI生成] 函数调用稳定性明显改进"


def test_apply_ai_generated_title_from_summary_when_title_missing() -> None:
    class _Content:
        title = None

    content = _Content()
    insight = LLMInsightItem(
        tweet_id="x3",
        ai_score=73,
        summary="新版本优化了推理吞吐并降低了延迟。适合高并发场景。",
        ai_title=None,
    )
    PipelineService._apply_ai_generated_title_if_missing(content_item=content, insight=insight)  # type: ignore[arg-type]
    assert content.title is not None
    assert content.title.startswith("[AI生成] ")
