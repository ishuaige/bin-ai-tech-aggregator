from __future__ import annotations

from typing import Any

import httpx

from core import get_settings


class TwitterApiClient:
    """TwitterAPI.io 客户端（基础封装）。"""

    def __init__(self) -> None:
        settings = get_settings()
        api_key = settings.TWITTERAPI_IO_API_KEY
        if not api_key:
            raise ValueError("缺少 TWITTERAPI_IO_API_KEY，请先在 .env 中配置。")

        self._base_url = settings.TWITTERAPI_IO_BASE_URL.rstrip("/")
        self._headers = {"x-api-key": api_key}

    async def _get(self, path: str, params: dict[str, str | int]) -> dict[str, Any]:
        """通用 GET 请求封装，统一鉴权头、超时和错误处理。"""
        url = f"{self._base_url}{path}"
        timeout = httpx.Timeout(20.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                url,
                headers=self._headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def fetch_user_followings(self, username: str) -> dict[str, Any]:
        """鉴权连通性 Demo 接口。"""
        return await self._get("/twitter/user/followings", params={"userName": username})

    async def fetch_user_last_tweets(
        self,
        user_name: str,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """
        获取某个用户最近推文。
        文档: /api-reference/endpoint/get_user_last_tweets
        """
        params: dict[str, str] = {"userName": user_name}
        if cursor:
            params["cursor"] = cursor
        return await self._get("/twitter/user/last_tweets", params=params)

    async def fetch_tweet_quotes(
        self,
        tweet_id: str,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """
        获取某条推文的引用推文列表。
        文档: /api-reference/endpoint/get_tweet_quote
        """
        params: dict[str, str] = {"tweetId": tweet_id}
        if cursor:
            params["cursor"] = cursor
        try:
            return await self._get("/twitter/tweet/quotes", params=params)
        except httpx.HTTPStatusError as exc:
            # 兼容平台可能存在的单复数路径差异（quote / quotes）。
            if exc.response.status_code != 404:
                raise
        return await self._get("/twitter/tweet/quote", params=params)

    async def fetch_tweet_advanced_search(
        self,
        query: str,
        query_type: str = "Latest",
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """
        高级搜索推文（按关键字/语法查询）。
        文档: /api-reference/endpoint/tweet_advanced_search
        """
        params: dict[str, str] = {
            "query": query,
            "queryType": query_type,
        }
        if cursor is not None:
            params["cursor"] = cursor
        return await self._get("/twitter/tweet/advanced_search", params=params)
