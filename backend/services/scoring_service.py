from __future__ import annotations

import math

from schemas import CrawlItem


class ScoringService:
    """规则打分服务：只做确定性计算，不消耗 AI token。"""

    @staticmethod
    def compute_hotness(item: CrawlItem) -> int:
        payload = item.raw_payload if isinstance(item.raw_payload, dict) else {}
        like_count = int(payload.get("likeCount") or 0)
        retweet_count = int(payload.get("retweetCount") or 0)
        reply_count = int(payload.get("replyCount") or 0)
        quote_count = int(payload.get("quoteCount") or 0)
        view_count = int(payload.get("viewCount") or 0)

        # 经验权重：转推>评论>点赞，浏览量做对数压缩，避免极端值失真。
        score = (
            like_count * 1.0
            + retweet_count * 2.0
            + reply_count * 1.6
            + quote_count * 2.2
            + math.log10(view_count + 1) * 8.0
        )
        normalized = int(min(100, round(score)))
        return max(0, normalized)

    def attach_hotness(self, items: list[CrawlItem]) -> list[CrawlItem]:
        return [item.model_copy(update={"hotness": self.compute_hotness(item)}) for item in items]
