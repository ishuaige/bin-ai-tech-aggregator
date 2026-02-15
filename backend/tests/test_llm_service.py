import pytest

from schemas import CrawlItem
from services.llm_service import LLMService


def _sample_items() -> list[CrawlItem]:
    return [
        CrawlItem(
            source="demo",
            tweet_id="1",
            author_username="alice",
            url="https://x.com/a/status/1",
            text="FastAPI and async Python update",
            published_at=None,
        )
    ]


def test_validate_summary_degraded_when_points_too_few() -> None:
    service = LLMService()
    result = service._validate_summary("- 只有一条")
    assert result.status == "degraded"
    assert result.failure_reason is not None


def test_validate_summary_extracts_insights_and_scores() -> None:
    service = LLMService()
    text = (
        "## 📊 AI分析总览\n"
        "- 综合评分: 86\n"
        "- 数据量: 20\n"
        "## 🔍 关键洞察\n"
        "- ID: 1001 | AI评分: 95 | 观点: 新推理架构在复杂任务上更稳定。\n"
        "- ID: 1002 | AI评分: 90 | 观点: 新模型在工具调用准确率上持续提升。\n"
        "- ID: 1003 | AI评分: 82 | 观点: 异步优化对中高并发 API 带来明显收益。\n"
    )
    result = service._validate_summary(text)
    assert result.status == "success"
    assert result.overall_score == 86
    assert len(result.insights) == 3
    assert result.insights[0].tweet_id == "1001"
    assert result.insights[0].ai_score == 95


def test_parse_batch_item_output_success() -> None:
    service = LLMService()
    text = (
        '[{"tweet_id":"1","ai_score":88,"summary":"这条资讯强调了异步队列在高并发任务调度中的价值。",'
        '"ai_title":"异步队列在高并发下的调度价值"}]'
    )
    insights = service._parse_batch_item_output(text, allowed_ids={"1", "2"})
    assert len(insights) == 1
    assert insights[0].tweet_id == "1"
    assert insights[0].ai_score == 88
    assert insights[0].ai_title == "异步队列在高并发下的调度价值"


@pytest.mark.asyncio
async def test_summarize_failed_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    service = LLMService()
    service._settings.ZAI_API_KEY = None
    result = await service.summarize(_sample_items())
    assert result.status == "failed"
    assert result.failure_reason == "missing_zai_api_key"
