import pytest

from models import ChannelPlatform, PushChannel
from services.notify_service import DigestItem, NotifyService


def _channel(platform: ChannelPlatform) -> PushChannel:
    return PushChannel(
        id=1,
        platform=platform,
        webhook_url="https://example.com/webhook",
        name=f"{platform.value}-channel",
        is_active=True,
    )


@pytest.mark.parametrize(
    ("platform", "key"),
    [
        (ChannelPlatform.WECHAT, "msgtype"),
        (ChannelPlatform.FEISHU, "msg_type"),
        (ChannelPlatform.DINGTALK, "msgtype"),
    ],
)
def test_build_payload_for_supported_platforms(platform: ChannelPlatform, key: str) -> None:
    service = NotifyService()
    payload = service._build_payload(_channel(platform), markdown="hello", digest_items=[])
    assert key in payload


def test_feishu_payload_uses_post_format() -> None:
    service = NotifyService()
    payload = service._build_payload(
        _channel(ChannelPlatform.FEISHU),
        markdown="line1\nline2",
        digest_items=[
            DigestItem(
                title="测试标题",
                url="https://x.com/a/status/1",
                source="alice",
                score=8,
                tags=["AI Agent"],
                publish_time="2026-02-15 00:00",
                ai_summary_list=["这是AI总结"],
            )
        ],
    )
    assert payload["msg_type"] == "post"
    assert "post" in payload["content"]
    rows = payload["content"]["post"]["zh_cn"]["content"]
    flat_text = " ".join(cell.get("text", "") for row in rows for cell in row)
    assert "资讯概览" in flat_text


@pytest.mark.asyncio
async def test_notify_channels_limit_feishu_to_top_10(monkeypatch: pytest.MonkeyPatch) -> None:
    service = NotifyService()
    feishu = PushChannel(
        id=1,
        platform=ChannelPlatform.FEISHU,
        webhook_url="https://example.com/feishu",
        name="feishu",
        is_active=True,
    )
    wechat = PushChannel(
        id=2,
        platform=ChannelPlatform.WECHAT,
        webhook_url="https://example.com/wechat",
        name="wechat",
        is_active=True,
    )
    digest_items = [
        DigestItem(
            title=f"title-{idx}",
            url=f"https://x.com/a/status/{idx}",
            source="alice",
            score=8,
            tags=["AI"],
            publish_time="2026-02-15 00:00",
            ai_summary_list=["summary"],
        )
        for idx in range(12)
    ]

    payload_map: dict[str, dict] = {}

    async def _fake_send_one(client, channel, payload):
        payload_map[channel.name] = payload
        return type(
            "_R",
            (),
            {
                "channel_id": channel.id,
                "channel_name": channel.name,
                "success": True,
                "status_code": 200,
                "error": None,
            },
        )()

    monkeypatch.setattr(service, "_send_one", _fake_send_one)
    await service.notify_channels(
        channels=[feishu, wechat],
        source_name="test",
        summary_markdown="summary",
        digest_items=digest_items,
    )

    feishu_rows = payload_map["feishu"]["content"]["post"]["zh_cn"]["content"]
    feishu_item_count = sum(1 for row in feishu_rows for cell in row if cell.get("tag") == "a")
    assert feishu_item_count == 10

    wechat_text = payload_map["wechat"]["markdown"]["content"]
    assert wechat_text.count("# 🚀 [") == 12
