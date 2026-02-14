"""
飞书 webhook 直连测试脚本（不依赖抓取和 LLM）。

用法：
1) 环境变量方式（推荐）
   FEISHU_WEBHOOK_URL='https://open.feishu.cn/open-apis/bot/v2/hook/xxx' \
   FEISHU_BOT_SECRET='可选，开启签名校验时填写' \
   python3 -m uv run python demo_send_feishu.py

2) 命令行参数方式
   python3 -m uv run python demo_send_feishu.py \
     --webhook 'https://open.feishu.cn/open-apis/bot/v2/hook/xxx' \
     --secret '可选'
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import time

import httpx


def _build_sign(secret: str) -> tuple[str, str]:
    """
    飞书签名算法：
    string_to_sign = f"{timestamp}\\n{secret}"
    sign = base64(hmac_sha256(string_to_sign, secret))
    """
    timestamp = str(int(time.time()))
    string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), string_to_sign, digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(digest).decode("utf-8")
    return timestamp, sign


def _build_payload(secret: str | None) -> dict:
    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "✅ 飞书直连测试",
                    "content": [
                        [{"tag": "text", "text": "这是一条来自后端 demo 的直连测试消息。\n"}],
                        [{"tag": "text", "text": "如果你看到这条，说明 webhook 通道可用。\n"}],
                        [{"tag": "text", "text": "排障建议：若业务链路失败，可先用本脚本确认通道。"}],
                    ],
                }
            }
        },
    }

    if secret:
        timestamp, sign = _build_sign(secret)
        payload["timestamp"] = timestamp
        payload["sign"] = sign

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a direct test message to Feishu webhook.")
    parser.add_argument("--webhook", default=os.getenv("FEISHU_WEBHOOK_URL", "").strip())
    parser.add_argument("--secret", default=os.getenv("FEISHU_BOT_SECRET", "").strip())
    args = parser.parse_args()

    if not args.webhook:
        print("缺少 webhook。请传入 --webhook 或设置 FEISHU_WEBHOOK_URL。")
        return

    payload = _build_payload(args.secret or None)
    timeout = httpx.Timeout(15.0)

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(args.webhook, json=payload)
        print(f"HTTP 状态码: {resp.status_code}")
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text[:1000]}
        print("响应内容:")
        print(json.dumps(body, ensure_ascii=False, indent=2))
    except Exception as exc:  # noqa: BLE001
        print(f"请求失败: {exc}")


if __name__ == "__main__":
    main()
