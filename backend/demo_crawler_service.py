import asyncio

import httpx

from core import get_settings
from services import CrawlerService


async def run_demo() -> None:
    settings = get_settings()
    crawler = CrawlerService()

    # 3.1: 按博主抓取（最近推文）
    author_result = await crawler.crawl_by_author(user_name=settings.TWITTERAPI_IO_DEMO_USERNAME)
    print(f"[3.1] 作者模式抓取条数: {len(author_result.items)}")
    if author_result.items:
        print(f"[3.1] 首条 DTO 字段: {author_result.items[0].model_dump().keys()}")

    # 免费层 QPS 很低（约 5 秒/次），这里主动等待，避免 429。
    await asyncio.sleep(5.2)

    # 3.2: 按关键字抓取（基于 tweet_advanced_search）
    keyword_result = await crawler.crawl_by_keyword(
        keyword="AI",
        query_type="Top",
    )
    print(f"[3.2] 关键字模式抓取条数: {len(keyword_result.items)}")

    # 3.3: 统一 DTO 验证（打印第一条结构）
    if keyword_result.items:
        print(f"[3.3] DTO 示例: {keyword_result.items[0].model_dump()}")


def main() -> None:
    try:
        asyncio.run(run_demo())
    except ValueError as exc:
        print(f"配置错误: {exc}")
    except httpx.HTTPStatusError as exc:
        print(f"接口请求失败: HTTP {exc.response.status_code}")
        print(f"响应内容: {exc.response.text[:500]}")


if __name__ == "__main__":
    main()
