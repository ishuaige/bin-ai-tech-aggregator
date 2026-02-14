import pytest

from services.crawler_service import CrawlerService


def test_extract_tweet_list_supports_data_tweets_shape() -> None:
    payload = {
        "data": {
            "tweets": [
                {"id": "1", "text": "hello"},
                {"id": "2", "text": "world"},
            ]
        }
    }
    tweets = CrawlerService._extract_tweet_list(payload)
    assert len(tweets) == 2
    assert tweets[0]["id"] == "1"


def test_to_crawl_item_maps_core_fields() -> None:
    service = CrawlerService.__new__(CrawlerService)
    tweet = {
        "id": "123",
        "text": "FastAPI rocks",
        "url": "https://x.com/a/status/123",
        "author": {"userName": "alice"},
        "createdAt": "2026-02-14T10:00:00Z",
    }
    item = service._to_crawl_item(tweet=tweet, source="author_timeline")
    assert item.tweet_id == "123"
    assert item.author_username == "alice"
    assert item.url.endswith("/123")
    assert item.text == "FastAPI rocks"


@pytest.mark.asyncio
async def test_crawl_by_author_returns_latest_10_items() -> None:
    class _Client:
        async def fetch_user_last_tweets(self, user_name: str, cursor: str | None = None):
            return {
                "tweets": [
                    {"id": str(i), "text": f"tweet-{i}", "author": {"userName": user_name}}
                    for i in range(20, 0, -1)
                ]
            }

    class _S:
        AUTHOR_FETCH_LIMIT = 10
        KEYWORD_LOOKBACK_HOURS = 24
        KEYWORD_MIN_LIKES = 30

    service = CrawlerService.__new__(CrawlerService)
    service._client = _Client()
    service._settings = _S()
    result = await service.crawl_by_author(user_name="alice")
    assert len(result.items) == 10
    assert result.items[0].tweet_id == "20"


def test_build_keyword_query_contains_min_faves() -> None:
    class _S:
        AUTHOR_FETCH_LIMIT = 10
        KEYWORD_LOOKBACK_HOURS = 24
        KEYWORD_MIN_LIKES = 30

    service = CrawlerService.__new__(CrawlerService)
    service._settings = _S()
    query = service._build_keyword_query("AI Agent")
    assert "AI Agent" in query
    assert "within_time:" not in query
    assert "min_faves:30" in query


def test_filter_keyword_items_filters_low_like_only() -> None:
    class _S:
        AUTHOR_FETCH_LIMIT = 10
        KEYWORD_LOOKBACK_HOURS = 24
        KEYWORD_MIN_LIKES = 30

    service = CrawlerService.__new__(CrawlerService)
    service._settings = _S()
    kept = service._to_crawl_item(
        tweet={
            "id": "1",
            "text": "new/high-like",
            "author": {"userName": "a"},
            "createdAt": "2026-02-15T00:00:00Z",
            "likeCount": 45,
        },
        source="tweet_advanced_search",
    )
    low_like = service._to_crawl_item(
        tweet={
            "id": "3",
            "text": "low-like",
            "author": {"userName": "c"},
            "createdAt": "2026-02-13T00:00:00Z",
            "likeCount": 3,
        },
        source="tweet_advanced_search",
    )

    filtered = service._filter_keyword_items([kept, low_like])
    assert [x.tweet_id for x in filtered] == ["1"]


def test_parse_datetime_supports_twitter_format() -> None:
    value = "Sat Feb 14 00:37:42 +0000 2026"
    dt = CrawlerService._parse_datetime(value)
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 2
    assert dt.day == 14
