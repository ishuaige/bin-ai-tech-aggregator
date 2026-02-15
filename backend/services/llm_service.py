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

# 动态导入 SDK，避免因缺少依赖导致整个服务崩溃
try:
    from zai import ZhipuAiClient
except Exception:  # pragma: no cover
    ZhipuAiClient = None  # type: ignore[assignment]


class LLMService:
    """LLM 服务：构建 Prompt、调用 GLM、校验输出格式。
    
    类似 Java 的 Service 层，封装了对大模型的调用逻辑。
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        # 构造函数中检查依赖
        if ZhipuAiClient is None:
            raise RuntimeError("未安装 zai-sdk，请先执行 `python3 -m uv sync`。")

    def build_messages(self, items: Sequence[CrawlItem]) -> list[dict[str, str]]:
        """
        构建聊天消息（Prompt）。
        
        Args:
            items: 抓取到的推文列表
            
        Returns:
            符合 OpenAI/GLM 格式的消息列表 [{"role": "user", "content": "..."}]
        """
        lines: list[str] = []
        # enumerate(items, start=1): 带索引遍历，索引从 1 开始
        for index, item in enumerate(items, start=1):
            lines.append(
                f"{index}. [{item.author_username}] {item.text}\n"
                f"   - url: {item.url}\n"
                f"   - published_at: {item.published_at}"
            )

        # Prompt Engineering (提示词工程)
        # 这里使用了 Few-Shot Prompting 或 结构化输出指令
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
        核心业务方法：生成内容总结。
        
        流程：
        1. 校验输入
        2. 构建 Prompt
        3. 调用大模型 (带重试机制)
        4. 解析返回结果 (Markdown -> 对象)
        """
        if not items:
            # 快速失败 (Fast Return)
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
        
        # 重试循环 (Retry Loop)
        for attempt in range(self._settings.GLM_MAX_RETRIES + 1):
            try:
                # await: 异步调用，不会阻塞主线程
                raw_content = await self._call_glm(api_key=api_key, messages=messages)
                last_raw_response = raw_content
                
                # 解析 Markdown 结果
                parsed = self._parse_summary_response(raw_content)
                parsed.model = self._settings.GLM_MODEL
                parsed.prompt_text = prompt_text
                parsed.raw_response_text = raw_content
                return parsed
                
            except Exception as e:
                last_error = str(e)
                # 简单的指数退避 (Exponential Backoff) 可以加在这里
                await asyncio.sleep(1) 

        # 重试耗尽，返回失败结果
        return LLMSummaryResult(
            status="failed",
            summary_markdown="",
            highlights=[],
            model=self._settings.GLM_MODEL,
            prompt_text=prompt_text,
            raw_response_text=last_raw_response,
            failure_reason=f"max_retries_exceeded: {last_error}",
        )
    
    # 私有方法 (Private Methods) 以 _ 开头
    # Python 没有 private 关键字，这是一种约定
    def _messages_to_text(self, messages: list[dict[str, str]]) -> str:
        return json.dumps(messages, ensure_ascii=False)

    async def _call_glm(self, api_key: str, messages: list[dict[str, str]]) -> str:
        """调用智谱 GLM API 的底层实现。"""
        # 实例化客户端
        client = ZhipuAiClient(api_key=api_key)
        
        # 运行在线程池中，因为 ZhipuAiClient 可能是同步的库
        # asyncio.to_thread 是 Python 3.9+ 的特性，用于把同步阻塞代码放到异步线程池运行
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=self._settings.GLM_MODEL,
            messages=messages,
            stream=False,
            temperature=0.1, # 低温度，让回答更确定、更严谨
        )
        return response.choices[0].message.content or ""

    def _parse_summary_response(self, text: str) -> LLMSummaryResult:
        """
        解析器：把大模型返回的非结构化 Markdown 文本，
        通过正则 (Regex) 提取为结构化的 LLMSummaryResult 对象。
        """
        # 1. 提取综合评分
        score_match = re.search(r"综合评分[:：]\s*(\d+)", text)
        overall_score = int(score_match.group(1)) if score_match else 0

        # 2. 提取每条洞察 (Insight)
        insights: list[LLMInsightItem] = []
        # 正则解释：
        # ID:\s*(.*?): 匹配 ID: 后的内容，非贪婪匹配
        # AI评分:\s*(\d+): 匹配分数
        # 观点:\s*(.*): 匹配观点内容
        pattern = re.compile(r"ID:\s*(.*?)\s*\|\s*AI评分:\s*(\d+)\s*\|\s*观点:\s*(.*)")
        
        for line in text.split("\n"):
            line = line.strip()
            if not line.startswith("-"):
                continue
                
            match = pattern.search(line)
            if match:
                insights.append(
                    LLMInsightItem(
                        tweet_id=match.group(1).strip(),
                        ai_score=int(match.group(2)),
                        summary=match.group(3).strip(),
                    )
                )

        return LLMSummaryResult(
            status="success",
            summary_markdown=text,
            overall_score=overall_score,
            insights=insights,
        )
