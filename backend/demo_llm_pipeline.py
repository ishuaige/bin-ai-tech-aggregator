import asyncio

from schemas import CrawlItem
from services import ContentFilterService, LLMService


async def run_demo() -> None:
    # 构造一组模拟抓取数据（包含重复和噪音，验证 3.4）
    raw_items = [
        CrawlItem(
            source="demo",
            tweet_id="1",
            author_username="alice",
            url="https://x.com/a/status/1",
            text="FastAPI 发布了新的异步性能优化，吞吐明显提升。",
            published_at=None,
        ),
        CrawlItem(
            source="demo",
            tweet_id="1",
            author_username="alice",
            url="https://x.com/a/status/1",
            text="FastAPI 发布了新的异步性能优化，吞吐明显提升。",
            published_at=None,
        ),
        CrawlItem(
            source="demo",
            tweet_id="2",
            author_username="bob",
            url="https://x.com/b/status/2",
            text="gm",
            published_at=None,
        ),
        CrawlItem(
            source="demo",
            tweet_id="3",
            author_username="carol",
            url="https://x.com/c/status/3",
            text="Zhipu GLM 在多轮推理任务上表现稳定。",
            published_at=None,
        ),
        CrawlItem(
            source="demo",
            tweet_id="4",
            author_username="dave",
            url="https://x.com/d/status/4",
            text="SQLite + SQLAlchemy AsyncSession 组合适合轻量级后台。",
            published_at=None,
        ),
    ]

    filter_service = ContentFilterService()
    cleaned_items = filter_service.clean_items(raw_items)
    print(f"[3.4] 清洗后条数: {len(cleaned_items)}")

    llm_service = LLMService()
    messages = llm_service.build_messages(cleaned_items)
    print(f"[3.5] Prompt 消息条数: {len(messages)}")

    result = await llm_service.summarize(cleaned_items)
    print(f"[3.6/3.7] 状态: {result.status}")
    print(f"[3.6/3.7] failure_reason: {result.failure_reason}")
    print(f"[3.6/3.7] 综合评分: {result.overall_score}")
    print(f"[3.6/3.7] 洞察条数: {len(result.insights)}")
    print(f"[3.6/3.7] 摘要预览: {result.summary_markdown[:300]}")


def main() -> None:
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
