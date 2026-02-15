from __future__ import annotations

from datetime import datetime
from typing import Any

from core import get_settings
from schemas import CrawlBatchResult, CrawlItem
from services.twitterapi_client import TwitterApiClient


class CrawlerService:
    """抓取服务：对外提供 author/keyword 两种抓取模式。
    
    该服务屏蔽了底层 API (TwitterApiClient) 的复杂性，
    统一返回 domain-specific 的 CrawlBatchResult 对象。
    """

    def __init__(self, client: TwitterApiClient | None = None) -> None:
        # 依赖注入 (Dependency Injection)
        # 允许传入 mock client 用于单元测试
        self._client = client or TwitterApiClient()
        self._settings = get_settings()

    async def crawl_by_author(
        self,
        user_name: str,
        cursor: str | None = None,
    ) -> CrawlBatchResult:
        """
        策略1：按博主抓取
        调用 get_user_last_tweets 端点获取某个博主的最新推文。
        """
        # 1. 调用底层 API
        payload = await self._client.fetch_user_last_tweets(user_name=user_name, cursor=cursor)
        
        # 2. 数据清洗与转换 (ETL)
        tweets = self._extract_tweet_list(payload)
        
        # 3. 业务规则过滤：只保留最新 N 条
        fetch_limit = max(1, self._settings.AUTHOR_FETCH_LIMIT)
        # List Comprehension (列表推导式)，Python 特有的优雅写法
        items = [self._to_crawl_item(tweet=tweet, source="author_timeline") for tweet in tweets][:fetch_limit]
        
        # 4. 提取分页游标
        next_cursor = self._extract_cursor(payload)
        
        return CrawlBatchResult(
            items=items,
            next_cursor=next_cursor,
            has_next_page=bool(next_cursor) or len(tweets) > len(items),
        )

    async def crawl_by_keyword(
        self,
        keyword: str,
        query_type: str = "Top",
        cursor: str | None = None,
    ) -> CrawlBatchResult:
        """
        策略2：按关键字抓取
        调用 tweet_advanced_search 端点搜索推文。
        """
        raw_keyword = keyword.strip()
        if not raw_keyword:
            return CrawlBatchResult(items=[], next_cursor=None, has_next_page=False)

        # 构造查询语句
        query = self._build_keyword_query(raw_keyword)
        
        search_payload = await self._client.fetch_tweet_advanced_search(
            query=query,
            query_type=query_type,
            cursor=cursor,
        )
        
        tweets = self._extract_tweet_list(search_payload)
        items = [self._to_crawl_item(tweet=tweet, source="tweet_advanced_search") for tweet in tweets]
        
        # 关键字模式通常噪音较大，这里做一层额外的过滤
        items = self._filter_keyword_items(items=items)
        
        next_cursor = self._extract_cursor(search_payload)
        return CrawlBatchResult(
            items=items,
            next_cursor=next_cursor,
            has_next_page=bool(next_cursor),
        )

    def _to_crawl_item(self, tweet: dict[str, Any], source: str) -> CrawlItem:
        """
        适配器模式 (Adapter Pattern)：
        把平台原始推文结构 (Dict)，转换为项目统一 DTO (CrawlItem)。
        """
        # dict.get("key") 类似 Java map.get("key")，如果 key 不存在返回 None，不会报错
        tweet_id = str(tweet.get("id") or tweet.get("tweetId") or "")
        author_username = self._extract_author(tweet)
        
        # 尝试多种路径获取 URL
        url = (
            tweet.get("url")
            or tweet.get("link")
            or (f"https://x.com/{author_username}/status/{tweet_id}" if tweet_id and author_username else "")
        )
        
        return CrawlItem(
            source=source,
            tweet_id=tweet_id,
            author_username=author_username,
            url=url,
            text=self._extract_text(tweet),
            published_at=self._parse_datetime(tweet.get("createdAt") or tweet.get("pubDate")),
            raw_payload=tweet,
        )

    @staticmethod
    def _extract_tweet_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
        """
        健壮性处理：兼容不同 API 返回结构。
        有些 API 可能会变，或者不同端点返回结构不一致。
        """
        # isinstance 检查类型
        if isinstance(payload.get("tweets"), list):
            return [x for x in payload["tweets"] if isinstance(x, dict)]

        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("tweets"), list):
            return [x for x in data["tweets"] if isinstance(x, dict)]
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
            
        return []

    # 以下辅助方法省略了具体实现，仅保留结构
    def _extract_cursor(self, payload: dict) -> str | None:
        return None
        
    def _extract_author(self, tweet: dict) -> str:
        return "unknown"
        
    def _extract_text(self, tweet: dict) -> str:
        return str(tweet.get("text", ""))
        
    def _parse_datetime(self, val: Any) -> datetime | None:
        return None
        
    def _build_keyword_query(self, keyword: str) -> str:
        return keyword
        
    def _filter_keyword_items(self, items: list[CrawlItem]) -> list[CrawlItem]:
        return items
