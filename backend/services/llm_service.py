from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Sequence
from typing import Any

from core import get_settings
from schemas import (
    CrawlItem,
    LLMBatchItemAnalysisResult,
    LLMInsightItem,
    LLMItemAnalysisResult,
    LLMSummaryResult,
)

try:
    from zai import ZhipuAiClient
except Exception:  # pragma: no cover
    ZhipuAiClient = None  # type: ignore[assignment]


class LLMService:
    """LLM 服务：构建 Prompt、调用 GLM、校验输出格式。"""

    def __init__(self) -> None:
        self._settings = get_settings()
        if ZhipuAiClient is None:
            raise RuntimeError("未安装 zai-sdk，请先执行 `python3 -m uv sync`。")

    def build_messages(self, items: Sequence[CrawlItem]) -> list[dict[str, str]]:
        """
        构建聊天消息（Prompt）。
        目标：输出 3-5 条中文 Markdown 要点，便于后续推送。
        """
        lines: list[str] = []
        for index, item in enumerate(items, start=1):
            lines.append(
                f"{index}. [{item.author_username}] {item.text}\n"
                f"   - url: {item.url}\n"
                f"   - published_at: {item.published_at}"
            )

        content = (
            "请基于以下推文内容，输出每一份技术资讯洞察。\n"
            "你必须严格按下面 Markdown 模板输出（不要加其他解释）：\n\n"
            "## 📊 AI分析总览\n"
            "- 综合评分: <0-100的整数>\n"
            "- 数据量: <数字>\n\n"
            "## 🔍 关键洞察\n"
            "- ID: <tweet_id> | AI评分: <0-100整数> | 观点: <20-60字，中文>\n"
            "- ID: <tweet_id> | AI评分: <0-100整数> | 观点: <20-60字，中文>\n"
            "- ID: <tweet_id> | AI评分: <0-100整数> | 观点: <20-60字，中文>\n\n"
            "要求：\n"
            "1) AI评分代表技术价值与可执行性。\n"
            "2) 观点必须可落地，不要空泛。\n"
            "3) 只使用输入里存在的 ID。\n\n"
            f"输入数据：\n{chr(10).join(lines)}"
        )

        return [
            {"role": "system", "content": "你是一个严谨的技术情报分析助手。"},
            {"role": "user", "content": content},
        ]

    async def summarize(self, items: Sequence[CrawlItem]) -> LLMSummaryResult:
        """
        3.5~3.7 主入口：
        - 3.5 构建 Prompt
        - 3.6 调用 GLM（超时 + 重试）
        - 3.7 解析并校验返回格式，失败时降级
        """
        if not items:
            return LLMSummaryResult(
                status="degraded",
                summary_markdown="- 有效信息不足，未生成总结。",
                highlights=[],
                model=self._settings.GLM_MODEL,
                failure_reason="no_input_items",
            )

        api_key = self._settings.ZAI_API_KEY
        messages = self.build_messages(items)
        prompt_text = self._messages_to_text(messages)
        if not api_key:
            return LLMSummaryResult(
                status="failed",
                summary_markdown="",
                highlights=[],
                model=self._settings.GLM_MODEL,
                prompt_text=prompt_text,
                failure_reason="missing_zai_api_key",
            )

        last_error: str | None = None
        last_raw_response: str | None = None
        for attempt in range(self._settings.GLM_MAX_RETRIES + 1):
            try:
                raw_content = await self._call_glm(api_key=api_key, messages=messages)
                last_raw_response = raw_content
                result = self._validate_summary(raw_content)
                return result.model_copy(
                    update={
                        "model": self._settings.GLM_MODEL,
                        "prompt_text": prompt_text,
                        "raw_response_text": last_raw_response,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                if attempt >= self._settings.GLM_MAX_RETRIES:
                    break
                # 指数退避：1s, 2s, 4s...
                await asyncio.sleep(2**attempt)

        return LLMSummaryResult(
            status="failed",
            summary_markdown="",
            highlights=[],
            model=self._settings.GLM_MODEL,
            prompt_text=prompt_text,
            raw_response_text=last_raw_response,
            failure_reason=f"glm_request_failed: {last_error}",
        )

    async def analyze_item(self, item: CrawlItem) -> LLMItemAnalysisResult:
        """
        单条资讯分析（用于缓存缺失补齐）。
        只返回 AI评分 + 观点，不让模型生成来源/热度等基础字段。
        """
        api_key = self._settings.ZAI_API_KEY
        messages = self._build_single_item_messages(item)
        prompt_text = self._messages_to_text(messages)
        if not api_key:
            return LLMItemAnalysisResult(
                status="failed",
                insight=None,
                model=self._settings.GLM_MODEL,
                prompt_text=prompt_text,
                failure_reason="missing_zai_api_key",
            )
        try:
            raw_content = await self._call_glm(api_key=api_key, messages=messages)
            score, summary = self._parse_single_item_output(raw_content)
            return LLMItemAnalysisResult(
                status="success",
                insight=LLMInsightItem(tweet_id=item.tweet_id, ai_score=score, summary=summary),
                model=self._settings.GLM_MODEL,
                prompt_text=prompt_text,
                raw_response_text=raw_content,
                failure_reason=None,
            )
        except Exception as exc:  # noqa: BLE001
            return LLMItemAnalysisResult(
                status="failed",
                insight=None,
                model=self._settings.GLM_MODEL,
                prompt_text=prompt_text,
                raw_response_text=None,
                failure_reason=str(exc),
            )

    async def analyze_items(self, items: Sequence[CrawlItem]) -> LLMBatchItemAnalysisResult:
        """
        批量分析多条资讯，减少 API 往返次数。
        输出要求：JSON 数组，每个元素包含 tweet_id/ai_score/summary。
        """
        if not items:
            return LLMBatchItemAnalysisResult(
                status="degraded",
                insights=[],
                model=self._settings.GLM_MODEL,
                failure_reason="no_input_items",
            )

        api_key = self._settings.ZAI_API_KEY
        messages = self._build_batch_item_messages(items)
        prompt_text = self._messages_to_text(messages)
        if not api_key:
            return LLMBatchItemAnalysisResult(
                status="failed",
                insights=[],
                model=self._settings.GLM_MODEL,
                prompt_text=prompt_text,
                failure_reason="missing_zai_api_key",
            )

        last_error: str | None = None
        last_raw_response: str | None = None
        for attempt in range(self._settings.GLM_MAX_RETRIES + 1):
            try:
                raw_content = await self._call_glm(api_key=api_key, messages=messages)
                last_raw_response = raw_content
                insights = self._parse_batch_item_output(raw_content, allowed_ids={item.tweet_id for item in items})
                status = "success" if insights else "degraded"
                return LLMBatchItemAnalysisResult(
                    status=status,
                    insights=insights,
                    model=self._settings.GLM_MODEL,
                    prompt_text=prompt_text,
                    raw_response_text=last_raw_response,
                    failure_reason=None if insights else "empty_batch_result",
                )
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                if attempt >= self._settings.GLM_MAX_RETRIES:
                    break
                await asyncio.sleep(2**attempt)

        return LLMBatchItemAnalysisResult(
            status="failed",
            insights=[],
            model=self._settings.GLM_MODEL,
            prompt_text=prompt_text,
            raw_response_text=last_raw_response,
            failure_reason=f"glm_batch_request_failed: {last_error}",
        )

    @staticmethod
    def _build_single_item_messages(item: CrawlItem) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": "你是一个严谨的技术分析助手。"},
            {
                "role": "user",
                "content": (
                    "请分析下面这条资讯，只输出两行：\n"
                    "AI评分: <0-100整数>\n"
                    "观点: <20-60字>\n\n"
                    f"tweet_id: {item.tweet_id}\n"
                    f"作者: {item.author_username}\n"
                    f"正文: {item.text}\n"
                    f"链接: {item.url}"
                ),
            },
        ]

    @staticmethod
    def _build_batch_item_messages(items: Sequence[CrawlItem]) -> list[dict[str, str]]:
        item_lines = []
        for idx, item in enumerate(items, start=1):
            item_lines.append(
                f"{idx}. tweet_id={item.tweet_id}\n"
                f"   author={item.author_username}\n"
                f"   text={item.text}\n"
                f"   url={item.url}"
            )
        content = (
            "请分析下面多条资讯，输出严格 JSON 数组，不要加 markdown 代码块，不要加解释。\n"
            "JSON 每个元素必须包含字段：tweet_id, ai_score, summary。\n"
            "要求：\n"
            "1) tweet_id 必须来自输入。\n"
            "2) ai_score 为 0-100 整数。\n"
            "3) summary 为 20-60 字中文，可执行、避免空话。\n\n"
            f"输入：\n{chr(10).join(item_lines)}"
        )
        return [
            {"role": "system", "content": "你是一个严谨的技术分析助手。"},
            {"role": "user", "content": content},
        ]

    async def _call_glm(self, api_key: str, messages: list[dict[str, str]]) -> str:
        """在子线程里执行 SDK 同步调用，避免阻塞 async 事件循环。"""
        client = ZhipuAiClient(api_key=api_key)

        def _sync_call() -> Any:
            return client.chat.completions.create(
                model=self._settings.GLM_MODEL,
                messages=messages,
                temperature=0.3,
            )

        response = await asyncio.wait_for(
            asyncio.to_thread(_sync_call),
            timeout=self._settings.GLM_TIMEOUT_SECONDS,
        )
        content = self._extract_content(response)
        if not content.strip():
            raise ValueError("glm_empty_response")
        return content

    @staticmethod
    def _extract_content(response: Any) -> str:
        """
        兼容 SDK 的对象/字典结构，尽量取到 choices[0].message.content。
        """
        if response is None:
            return ""

        # 对象风格：response.choices[0].message.content
        choices = getattr(response, "choices", None)
        if choices and len(choices) > 0:
            first = choices[0]
            message = getattr(first, "message", None)
            content = getattr(message, "content", None)
            if isinstance(content, str):
                return content

        # 字典风格：response["choices"][0]["message"]["content"]
        if isinstance(response, dict):
            r_choices = response.get("choices")
            if isinstance(r_choices, list) and r_choices:
                first = r_choices[0]
                if isinstance(first, dict):
                    message = first.get("message")
                    if isinstance(message, dict) and isinstance(message.get("content"), str):
                        return message["content"]
        return ""

    def _validate_summary(self, summary_markdown: str) -> LLMSummaryResult:
        """
        解析并校验输出：
        - 必须至少包含 3 条 Markdown 列表项
        - 不满足时降级返回，并带失败原因
        """
        lines = [line.strip() for line in summary_markdown.splitlines() if line.strip()]
        highlights = [line[2:].strip() for line in lines if line.startswith("- ") and len(line) > 2]
        overall_score = self._extract_overall_score(lines)
        insights = self._extract_insights(lines)

        if len(highlights) < 3 or len(insights) < 3:
            return LLMSummaryResult(
                status="degraded",
                summary_markdown=summary_markdown,
                highlights=highlights,
                overall_score=overall_score,
                insights=insights,
                failure_reason="invalid_summary_format_or_too_few_points",
            )

        return LLMSummaryResult(
            status="success",
            summary_markdown=summary_markdown,
            highlights=highlights[:5],
            overall_score=overall_score,
            insights=insights[:5],
            failure_reason=None,
        )

    @staticmethod
    def _messages_to_text(messages: list[dict[str, str]]) -> str:
        blocks: list[str] = []
        for message in messages:
            role = message.get("role", "unknown")
            content = message.get("content", "")
            blocks.append(f"[{role}]\n{content}")
        return "\n\n".join(blocks)

    @staticmethod
    def _parse_single_item_output(content: str) -> tuple[int, str]:
        score_match = re.search(r"AI评分[:：]\s*(\d{1,3})", content)
        summary_match = re.search(r"观点[:：]\s*(.+)", content)
        score = int(score_match.group(1)) if score_match else 60
        score = max(0, min(100, score))
        summary = summary_match.group(1).strip() if summary_match else content.strip()
        if len(summary) > 120:
            summary = f"{summary[:120]}..."
        return score, summary

    @staticmethod
    def _parse_batch_item_output(content: str, allowed_ids: set[str]) -> list[LLMInsightItem]:
        cleaned = content.strip()
        if "```" in cleaned:
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]

        payload = json.loads(cleaned)
        if not isinstance(payload, list):
            return []

        results: list[LLMInsightItem] = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            tweet_id = str(row.get("tweet_id") or "").strip()
            if not tweet_id or tweet_id not in allowed_ids:
                continue
            score = int(row.get("ai_score") or 0)
            score = max(0, min(100, score))
            summary = str(row.get("summary") or "").strip()
            if not summary:
                continue
            if len(summary) > 120:
                summary = f"{summary[:120]}..."
            results.append(
                LLMInsightItem(
                    tweet_id=tweet_id,
                    ai_score=score,
                    summary=summary,
                )
            )

        dedup: dict[str, LLMInsightItem] = {}
        for item in results:
            dedup[item.tweet_id] = item
        return list(dedup.values())

    @staticmethod
    def _extract_overall_score(lines: list[str]) -> int | None:
        pattern = re.compile(r"综合评分[:：]\s*(\d{1,3})")
        for line in lines:
            match = pattern.search(line)
            if match:
                value = int(match.group(1))
                return max(0, min(100, value))
        return None

    @staticmethod
    def _extract_insights(lines: list[str]) -> list[LLMInsightItem]:
        """
        解析形如：
        - 来源: xxx | 热度: 82 | AI评分: 90 | 观点: xxx
        """
        result: list[LLMInsightItem] = []
        pattern = re.compile(
            r"^-+\s*ID[:：]\s*(?P<tweet_id>[^|]+)\|\s*AI评分[:：]\s*(?P<score>\d{1,3})\s*\|\s*观点[:：]\s*(?P<summary>.+)$"
        )
        for line in lines:
            match = pattern.match(line)
            if not match:
                continue
            score = max(0, min(100, int(match.group("score"))))
            result.append(
                LLMInsightItem(
                    tweet_id=match.group("tweet_id").strip(),
                    ai_score=score,
                    summary=match.group("summary").strip(),
                )
            )
        return result
