import asyncio
import json

import httpx

from core import get_settings
from services.twitterapi_client import TwitterApiClient


async def run_demo() -> None:
    """
    最小 Demo：
    1) 读取配置
    2) 用 x-api-key 请求 TwitterAPI.io
    3) 打印结果摘要，确认是否接入成功
    """
    settings = get_settings()
    username = settings.TWITTERAPI_IO_DEMO_USERNAME

    client = TwitterApiClient()
    data = await client.fetch_user_followings(username=username)

    # 只打印前 1000 个字符，避免输出过长
    preview = json.dumps(data, ensure_ascii=False)[:1000]
    print("TwitterAPI.io 鉴权调用成功")
    print(f"测试账号: {username}")
    print(f"返回预览: {preview}")


def main() -> None:
    try:
        asyncio.run(run_demo())
    except ValueError as exc:
        # 常见情况：还没在 .env 里配置 TWITTERAPI_IO_API_KEY
        print(f"配置错误: {exc}")
    except httpx.HTTPStatusError as exc:
        # 常见情况：API key 无效或额度不足，接口会返回 4xx/5xx
        print(f"接口请求失败: HTTP {exc.response.status_code}")
        print(f"响应内容: {exc.response.text[:500]}")


if __name__ == "__main__":
    main()
