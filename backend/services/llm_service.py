from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from core import get_settings
from schemas import CrawlItem, LLMSummaryResult

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
            "请基于以下推文内容，提炼 3-5 条中文技术要点。\n"
            "输出要求：\n"
            "1) 必须使用 Markdown 无序列表（每条以 `- ` 开头）。\n"
            "2) 每条 20-60 字，避免空话。\n"
            "3) 若内容不足，请明确说明“有效信息不足”。\n\n"
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
                failure_reason="no_input_items",
            )

        api_key = self._settings.ZAI_API_KEY
        if not api_key:
            return LLMSummaryResult(
                status="failed",
                summary_markdown="",
                highlights=[],
                failure_reason="missing_zai_api_key",
            )

        messages = self.build_messages(items)

        last_error: str | None = None
        for attempt in range(self._settings.GLM_MAX_RETRIES + 1):
            try:
                raw_content = await self._call_glm(api_key=api_key, messages=messages)
                return self._validate_summary(raw_content)
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
            failure_reason=f"glm_request_failed: {last_error}",
        )

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
        lines = [line.strip() for line in summary_markdown.splitlines()]
        highlights = [line[2:].strip() for line in lines if line.startswith("- ") and len(line) > 2]

        if len(highlights) < 3:
            return LLMSummaryResult(
                status="degraded",
                summary_markdown=summary_markdown,
                highlights=highlights,
                failure_reason="invalid_summary_format_or_too_few_points",
            )

        return LLMSummaryResult(
            status="success",
            summary_markdown=summary_markdown,
            highlights=highlights[:5],
            failure_reason=None,
        )
