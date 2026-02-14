from __future__ import annotations

from datetime import datetime
from typing import Any

from core import get_settings
from schemas import CrawlBatchResult, CrawlItem
from services.twitterapi_client import TwitterApiClient


class CrawlerService:
    """抓取服务：对外提供 author/keyword 两种抓取模式。"""

    def __init__(self, client: TwitterApiClient | None = None) -> None:
        self._client = client or TwitterApiClient()
        self._settings = get_settings()

    async def crawl_by_author(
        self,
        user_name: str,
        cursor: str | None = None,
    ) -> CrawlBatchResult:
        """3.1 按博主抓取：调用 get_user_last_tweets 端点。"""
        payload = await self._client.fetch_user_last_tweets(user_name=user_name, cursor=cursor)
        tweets = self._extract_tweet_list(payload)
        # 作者模式只保留最新 N 条，避免一次取太多导致噪音上升。
        fetch_limit = max(1, self._settings.AUTHOR_FETCH_LIMIT)
        items = [self._to_crawl_item(tweet=tweet, source="author_timeline") for tweet in tweets][:fetch_limit]
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
        3.2 按关键字抓取：调用 tweet_advanced_search 端点。
        """
        raw_keyword = keyword.strip()
        if not raw_keyword:
            return CrawlBatchResult(items=[], next_cursor=None, has_next_page=False)

        # 关键字模式：仅使用 Top + 最低点赞阈值，先确保可稳定检索。
        query = self._build_keyword_query(raw_keyword)
        search_payload = await self._client.fetch_tweet_advanced_search(
            query=query,
            query_type=query_type,
            cursor=cursor,
        )
        tweets = self._extract_tweet_list(search_payload)
        items = [self._to_crawl_item(tweet=tweet, source="tweet_advanced_search") for tweet in tweets]
        items = self._filter_keyword_items(items=items)
        next_cursor = self._extract_cursor(search_payload)
        return CrawlBatchResult(
            items=items,
            next_cursor=next_cursor,
            has_next_page=bool(next_cursor),
        )

    def _to_crawl_item(self, tweet: dict[str, Any], source: str) -> CrawlItem:
        """把平台原始推文结构，转换为项目统一 DTO。"""
        tweet_id = str(tweet.get("id") or tweet.get("tweetId") or "")
        author_username = self._extract_author(tweet)
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
        兼容不同返回结构：
        - {"tweets": [...]}
        - {"data": {"tweets": [...]}}
        - {"data": [...]}
        """
        if isinstance(payload.get("tweets"), list):
            return [x for x in payload["tweets"] if isinstance(x, dict)]

        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("tweets"), list):
            return [x for x in data["tweets"] if isinstance(x, dict)]
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        return []

    @staticmethod
    def _extract_cursor(payload: dict[str, Any]) -> str | None:
        if isinstance(payload.get("next_cursor"), str):
            return payload["next_cursor"]
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("next_cursor"), str):
            return data["next_cursor"]
        if isinstance(payload.get("cursor"), str):
            return payload["cursor"]
        return None

    @staticmethod
    def _extract_text(tweet: dict[str, Any]) -> str:
        return str(tweet.get("text") or tweet.get("fullText") or tweet.get("description") or "")

    @staticmethod
    def _extract_author(tweet: dict[str, Any]) -> str:
        """
        常见结构：
        - tweet["author"]["userName"]
        - tweet["author"]["username"]
        - tweet["authorName"]
        """
        author = tweet.get("author")
        if isinstance(author, dict):
            if isinstance(author.get("userName"), str):
                return author["userName"]
            if isinstance(author.get("username"), str):
                return author["username"]
        if isinstance(tweet.get("authorName"), str):
            return tweet["authorName"]
        return ""

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        text = value.strip()

        # 1) 优先按 ISO8601 解析（如 2026-02-14T10:00:00Z）
        iso_text = text.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(iso_text)
        except ValueError:
            pass

        # 2) 兼容 Twitter 常见时间格式（如 Sat Feb 14 00:37:42 +0000 2026）
        for fmt in ("%a %b %d %H:%M:%S %z %Y", "%a %b %d %H:%M:%S %Y"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    def _build_keyword_query(self, keyword: str) -> str:
        """
        基于 Twitter Advanced Search 语法拼接查询：
        - min_faves:N      -> 最低点赞阈值
        """
        min_faves = max(0, self._settings.KEYWORD_MIN_LIKES)
        return f"{keyword} min_faves:{min_faves}"

    def _filter_keyword_items(self, items: list[CrawlItem]) -> list[CrawlItem]:
        """
        双保险过滤：
        - likeCount >= 阈值
        说明：即使上游 query 已带过滤条件，本地仍再过滤一次，避免接口返回不稳定。
        """
        min_likes = max(0, self._settings.KEYWORD_MIN_LIKES)
        filtered: list[CrawlItem] = []

        for item in items:
            like_count = int(item.raw_payload.get("likeCount") or 0)
            if like_count < min_likes:
                continue
            filtered.append(item)
        return filtered
