from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

from core import app_now
from models import ChannelPlatform, PushChannel

logger = logging.getLogger(__name__)


@dataclass
class NotifyResult:
    channel_id: int
    channel_name: str
    success: bool
    status_code: int | None = None
    error: str | None = None


@dataclass
class DigestItem:
    title: str
    url: str
    source: str
    score: int | None = None  # 0-10
    tags: list[str] = field(default_factory=list)
    publish_time: str = "-"
    ai_summary_list: list[str] = field(default_factory=list)


class NotifyService:
    """Webhook 推送服务，支持企业微信/飞书/钉钉。"""

    def build_markdown(
        self,
        source_name: str,
        summary_markdown: str,
        digest_items: list[DigestItem] | None = None,
    ) -> str:
        now_text = app_now().strftime("%Y-%m-%d %H:%M")
        if digest_items:
            chunks = [
                f"## 🚀 AI 技术情报速递\n> 🧭 监控源: `{source_name}`\n> 🕒 生成时间: `{now_text}`\n",
            ]
            for item in digest_items:
                tags = "、".join(item.tags) if item.tags else "-"
                score = item.score if item.score is not None else "-"
                stars = self._score_stars(item.score)
                ai_lines = item.ai_summary_list or ["AI 暂未给出提炼。"]
                ai_text = "\n".join([f"  - {line}" for line in ai_lines[:3]])
                chunks.append(
                    "\n".join(
                        [
                            f"# 🚀 [{item.title}]({item.url})",
                            "",
                            "**📊 资讯概览**",
                            f"- **🔍 来源**：#{item.source}#",
                            f"- **⭐️ AI 推荐度**：{stars} ({score}/10)",
                            f"- **🏷️ 领域标签**：`#{tags}#`",
                            f"- **🕒 发布于**：{item.publish_time}",
                            "- **🤖 AI 核心提炼**：",
                            ai_text,
                            "",
                            "---",
                        ]
                    )
                )
            return "\n".join(chunks)

        return (
            f"## 🚀 AI 技术情报速递\n"
            f"> 🧭 监控源: `{source_name}`\n"
            f"> 🕒 生成时间: `{now_text}`\n\n"
            f"---\n\n"
            f"{summary_markdown}\n"
        )

    async def notify_channels(
        self,
        channels: list[PushChannel],
        source_name: str,
        summary_markdown: str,
        digest_items: list[DigestItem] | None = None,
    ) -> list[NotifyResult]:
        if not channels:
            return []

        timeout = httpx.Timeout(15.0)
        results: list[NotifyResult] = []

        async with httpx.AsyncClient(timeout=timeout) as client:
            tasks = []
            for channel in channels:
                # 飞书渠道只推送前10条（默认 digest_items 已按热度降序）。
                channel_items = digest_items or []
                platform = channel.platform.value if isinstance(channel.platform, ChannelPlatform) else str(channel.platform)
                if platform == ChannelPlatform.FEISHU.value:
                    channel_items = channel_items[:10]

                markdown = self.build_markdown(
                    source_name=source_name,
                    summary_markdown=summary_markdown,
                    digest_items=channel_items,
                )
                payload = self._build_payload(channel=channel, markdown=markdown, digest_items=channel_items)
                tasks.append(self._send_one(client=client, channel=channel, payload=payload))

            if tasks:
                results = list(await asyncio.gather(*tasks))

        return results

    def _build_payload(self, channel: PushChannel, markdown: str, digest_items: list[DigestItem]) -> dict:
        platform = channel.platform.value if isinstance(channel.platform, ChannelPlatform) else str(channel.platform)
        title = "AI 技术资讯摘要"

        if platform == ChannelPlatform.WECHAT.value:
            return {
                "msgtype": "markdown",
                "markdown": {"content": markdown},
            }

        if platform == ChannelPlatform.FEISHU.value:
            return self._build_feishu_post_payload(markdown=markdown, title=title, digest_items=digest_items)

        if platform == ChannelPlatform.DINGTALK.value:
            return {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": markdown,
                },
            }

        raise ValueError(f"unsupported_platform: {platform}")

    def _build_feishu_post_payload(self, markdown: str, title: str, digest_items: list[DigestItem]) -> dict:
        if digest_items:
            content_rows: list[list[dict[str, str]]] = []
            for item in digest_items:
                tags = "、".join(item.tags) if item.tags else "-"
                score = item.score if item.score is not None else "-"
                stars = self._score_stars(item.score)
                content_rows.append([{"tag": "text", "text": "🚀 "}, {"tag": "a", "text": item.title, "href": item.url}])
                content_rows.append([{"tag": "text", "text": "📊 资讯概览"}])
                content_rows.append([{"tag": "text", "text": f"🔍 来源：#{item.source}#"}])
                content_rows.append([{"tag": "text", "text": f"⭐️ AI 推荐度：{stars} ({score}/10)"}])
                content_rows.append([{"tag": "text", "text": f"🏷️ 领域标签：#{tags}#"}])
                content_rows.append([{"tag": "text", "text": f"🕒 发布于：{item.publish_time}"}])
                content_rows.append([{"tag": "text", "text": "🤖 AI 核心提炼："}])
                for line in (item.ai_summary_list or ["AI 暂未给出提炼。"])[:3]:
                    content_rows.append([{"tag": "text", "text": f"• {line}"}])
                content_rows.append([{"tag": "text", "text": "----------------"}])
            return {
                "msg_type": "post",
                "content": {
                    "post": {
                        "zh_cn": {
                            "title": title,
                            "content": content_rows,
                        }
                    }
                },
            }

        lines = [line for line in markdown.splitlines() if line.strip()]
        content_rows: list[list[dict[str, str]]] = []
        for line in lines:
            content_rows.append([{"tag": "text", "text": f"{line}\n"}])

        return {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": content_rows,
                    }
                }
            },
        }

    @staticmethod
    def _score_stars(score: int | None) -> str:
        if score is None:
            return "☆☆☆☆☆"
        stars = max(0, min(5, round(score / 2)))
        return "★" * stars + "☆" * (5 - stars)

    async def _send_one(self, client: httpx.AsyncClient, channel: PushChannel, payload: dict) -> NotifyResult:
        webhook_for_log = self._mask_webhook_url(channel.webhook_url)
        logger.info(
            "webhook_send_start channel=%s platform=%s webhook=%s payload_keys=%s",
            channel.name,
            channel.platform,
            webhook_for_log,
            list(payload.keys()),
        )
        try:
            resp = await client.post(channel.webhook_url, json=payload)
            resp.raise_for_status()
            body_preview = resp.text[:500] if resp.text else ""
            logger.info(
                "webhook_send_done channel=%s platform=%s webhook=%s status=%s response=%s",
                channel.name,
                channel.platform,
                webhook_for_log,
                resp.status_code,
                body_preview,
            )
            return NotifyResult(
                channel_id=channel.id,
                channel_name=channel.name,
                success=True,
                status_code=resp.status_code,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "webhook_send_failed channel=%s platform=%s webhook=%s",
                channel.name,
                channel.platform,
                webhook_for_log,
            )
            return NotifyResult(
                channel_id=channel.id,
                channel_name=channel.name,
                success=False,
                error=str(exc),
            )

    @staticmethod
    def _mask_webhook_url(url: str) -> str:
        try:
            parsed = urlparse(url)
            path = parsed.path or ""
            if len(path) > 10:
                path = f"{path[:6]}...{path[-4:]}"
            return f"{parsed.scheme}://{parsed.netloc}{path}"
        except Exception:
            if len(url) > 12:
                return f"{url[:6]}...{url[-4:]}"
            return url
