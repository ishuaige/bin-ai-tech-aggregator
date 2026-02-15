from __future__ import annotations

import os
import tempfile
from datetime import datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.base import Base
from db.session import get_db
from main import app
from models import ContentItem, PushLog, PushLogItem, PushStatus
from routers import contents as contents_router_module
from schemas import LLMBatchItemAnalysisResult, LLMInsightItem


@pytest_asyncio.fixture
async def test_client():
    fd, db_path = tempfile.mkstemp(prefix="api_phase4_", suffix=".db")
    os.close(fd)
    db_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(db_url, future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.mark.asyncio
async def test_phase4_api_flow(test_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, session_factory = test_client

    health = await client.get("/health")
    assert health.status_code == 200
    assert health.json()["data"]["status"] == "ok"

    ready = await client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["data"]["status"] == "ready"

    create_source = await client.post(
        "/api/sources",
        json={"type": "author", "value": "karpathy", "is_active": True, "remark": "demo"},
    )
    assert create_source.status_code == 200
    source_id = create_source.json()["data"]["id"]

    list_source = await client.get("/api/sources?page=1&page_size=10&type=author&is_active=true")
    assert list_source.status_code == 200
    assert list_source.json()["data"]["meta"]["total"] == 1

    update_source = await client.put(f"/api/sources/{source_id}", json={"value": "openai"})
    assert update_source.status_code == 200
    assert update_source.json()["data"]["value"] == "openai"

    create_channel = await client.post(
        "/api/channels",
        json={
            "platform": "feishu",
            "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/demo",
            "name": "feishu-main",
            "is_active": True,
        },
    )
    assert create_channel.status_code == 200
    channel_id = create_channel.json()["data"]["id"]

    list_channels = await client.get("/api/channels?page=1&page_size=10&platform=feishu")
    assert list_channels.status_code == 200
    assert list_channels.json()["data"]["meta"]["total"] == 1

    update_channel = await client.put(f"/api/channels/{channel_id}", json={"name": "feishu-main-2"})
    assert update_channel.status_code == 200
    assert update_channel.json()["data"]["name"] == "feishu-main-2"

    create_binding = await client.post(
        "/api/source-channel-bindings",
        json={"source_id": source_id, "channel_id": channel_id},
    )
    assert create_binding.status_code == 200
    binding_id = create_binding.json()["data"]["id"]

    list_bindings = await client.get(f"/api/source-channel-bindings?page=1&page_size=10&source_id={source_id}")
    assert list_bindings.status_code == 200
    assert list_bindings.json()["data"]["meta"]["total"] == 1

    run_now = await client.post("/api/jobs/run-now")
    assert run_now.status_code == 200
    assert run_now.json()["message"] == "accepted"
    assert run_now.json()["data"]["status"] == "accepted"

    async with session_factory() as db:
        push_log = PushLog(
            source_id=source_id,
            status=PushStatus.SUCCESS,
            raw_content='[{"text":"hello"}]',
            ai_summary="summary markdown",
            created_at=datetime.now(),
        )
        db.add(push_log)
        await db.flush()
        content_item = ContentItem(
            platform="twitter",
            source_type="author_timeline",
            external_id="tweet-1001",
            author_name="openai",
            url="https://x.com/openai/status/1001",
            title=None,
            content_text="这是一条待手动分析的资讯正文，包含模型能力升级信息。",
            content_hash="hash-1001",
            published_at=datetime.now(),
            raw_payload='{"demo": true}',
            hotness=88,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.add(content_item)
        await db.flush()
        db.add(
            PushLogItem(
                push_log_id=push_log.id,
                tweet_id="tweet-1001",
                source="author_timeline",
                author_username="openai",
                url="https://x.com/openai/status/1001",
                text="这是一条待手动分析的资讯正文，包含模型能力升级信息。",
                hotness=88,
                ai_score=85,
                created_at=datetime.now(),
            )
        )
        await db.commit()

    async def _fake_analyze_items(_items):
        return LLMBatchItemAnalysisResult(
            status="success",
            insights=[
                LLMInsightItem(
                    tweet_id="tweet-1001",
                    ai_score=92,
                    summary="这条资讯强调了模型在工具调用可靠性上的提升。",
                    ai_title="模型工具调用可靠性提升",
                )
            ],
            model="glm-test",
            prompt_text="prompt",
            raw_response_text='[{"ok":true}]',
            failure_reason=None,
        )

    monkeypatch.setattr(contents_router_module._llm_service, "analyze_items", _fake_analyze_items)

    list_contents = await client.get("/api/contents?page=1&page_size=10")
    assert list_contents.status_code == 200
    assert list_contents.json()["data"]["meta"]["total"] >= 1

    analyze_content = await client.post(f"/api/contents/{content_item.id}/analyze")
    assert analyze_content.status_code == 200
    assert analyze_content.json()["data"]["ai"]["status"] == "success"
    assert analyze_content.json()["data"]["title"].startswith("[AI生成]")

    analyze_content_404 = await client.post("/api/contents/99999/analyze")
    assert analyze_content_404.status_code == 404

    list_logs = await client.get("/api/logs?page=1&page_size=10&status=success")
    assert list_logs.status_code == 200
    assert list_logs.json()["data"]["meta"]["total"] == 1
    log_id = list_logs.json()["data"]["items"][0]["id"]

    detail = await client.get(f"/api/logs/{log_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["ai_summary"] == "summary markdown"

    overview = await client.get("/api/dashboard/overview")
    assert overview.status_code == 200
    assert "today_run_count" in overview.json()["data"]

    delete_source = await client.delete(f"/api/sources/{source_id}")
    assert delete_source.status_code == 409

    delete_binding = await client.delete(f"/api/source-channel-bindings/{binding_id}")
    assert delete_binding.status_code == 200
    assert delete_binding.json()["data"]["deleted"] is True

    delete_channel = await client.delete(f"/api/channels/{channel_id}")
    assert delete_channel.status_code == 200
    assert delete_channel.json()["data"]["deleted"] is True
