from __future__ import annotations

import re

from schemas import CrawlItem


class ContentFilterService:
    """抓取结果清洗服务：去重 + 基础噪音过滤。"""

    _NOISE_PATTERNS = (
        re.compile(r"^\s*(gm|gn|good morning|good night)\s*$", re.IGNORECASE),
        re.compile(r"^\s*(早安|晚安|打卡)\s*$"),
    )

    def clean_items(self, items: list[CrawlItem]) -> list[CrawlItem]:
        """
        清洗规则：
        1) 去掉空文本
        2) 去掉明显无信息噪音
        3) 同一批次内去重（tweet_id 或归一化文本）
        """
        dedup_keys: set[str] = set()
        cleaned: list[CrawlItem] = []

        for item in items:
            text = self._normalize_text(item.text)
            if not text:
                continue
            if self._is_noise(text):
                continue

            # 优先用 tweet_id 去重；没有 tweet_id 时退化为文本去重。
            key = f"id:{item.tweet_id}" if item.tweet_id else f"text:{text.lower()}"
            if key in dedup_keys:
                continue
            dedup_keys.add(key)

            cleaned.append(item.model_copy(update={"text": text}))

        return cleaned

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.split()).strip()

    def _is_noise(self, text: str) -> bool:
        # 过短文本通常不具备技术信息价值
        if len(text) < 8:
            return True

        # 纯链接/纯@提及，一般无可读内容
        if re.fullmatch(r"(https?://\S+\s*)+", text):
            return True
        if re.fullmatch(r"(@\w+\s*)+", text):
            return True

        return any(pattern.match(text) for pattern in self._NOISE_PATTERNS)
