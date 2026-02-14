# 项目指令手册（本地开发）

> 目的：把常用命令集中到一处，避免每次翻聊天记录。

## 0. 目录约定

- 项目根目录：`/Users/dogbin/Documents/code/bin-ai-tech-aggregator`
- 后端目录：`/Users/dogbin/Documents/code/bin-ai-tech-aggregator/backend`

---

## 1. 首次初始化

```bash
cd /Users/dogbin/Documents/code/bin-ai-tech-aggregator/backend
python3 -m uv sync
cp -n .env.example .env
python3 -m uv run python init_db.py
```

说明：
- `uv sync`：安装依赖并生成/同步虚拟环境。
- `init_db.py`：根据 SQLAlchemy 模型自动建表。

---

## 2. 启动后端

```bash
cd /Users/dogbin/Documents/code/bin-ai-tech-aggregator/backend
python3 -m uv run uvicorn main:app --reload
```

健康检查：
```bash
curl http://127.0.0.1:8000/health
```

---

## 3. 手动触发全流程（抓取 -> AI -> 推送）

```bash
curl -X POST http://127.0.0.1:8000/internal/jobs/run-now
```

返回字段说明：
- `total_sources`：参与执行的启用监控源数量。
- `success_count`：成功数量。
- `failed_count`：失败数量。

---

## 4. 只测某个 Webhook 渠道（不走抓取/AI）

先查 `channel_id`：
```bash
cd /Users/dogbin/Documents/code/bin-ai-tech-aggregator/backend
python3 -m uv run python - <<'PY'
import sqlite3
c=sqlite3.connect("app.db")
print(c.execute("select id,name,platform,is_active from push_channels order by id").fetchall())
PY
```

测试指定渠道：
```bash
curl -X POST http://127.0.0.1:8000/internal/webhook/test \
  -H "Content-Type: application/json" \
  -d '{"channel_id":1,"source_name":"manual-test","summary_markdown":"- ✅ 渠道测试消息"}'
```

---

## 5. 飞书直连 Demo（完全独立）

```bash
cd /Users/dogbin/Documents/code/bin-ai-tech-aggregator/backend
FEISHU_WEBHOOK_URL='你的webhook' \
FEISHU_BOT_SECRET='你的secret(可选)' \
python3 -m uv run python demo_send_feishu.py
```

---

## 6. TwitterAPI 接入验证

鉴权验证：
```bash
cd /Users/dogbin/Documents/code/bin-ai-tech-aggregator/backend
python3 -m uv run python demo_twitterapi_auth.py
```

抓取服务验证（author + keyword）：
```bash
python3 -m uv run python demo_crawler_service.py
```

---

## 7. GLM 调用验证

```bash
cd /Users/dogbin/Documents/code/bin-ai-tech-aggregator/backend
python3 -m uv run python demo_llm_pipeline.py
```

如果提示 `missing_zai_api_key`，需要先在 `.env` 配置：
- `ZAI_API_KEY=...`
- `GLM_MODEL=glm-4.5-air`
- `LLM_ANALYZE_BATCH_SIZE=8`（批量分析大小）

抓取过滤相关配置（`.env`）：
- `AUTHOR_FETCH_LIMIT=10`（作者模式最多抓取条数）
- `KEYWORD_MIN_LIKES=30`（关键字模式最低点赞阈值）

---

## 8. 测试命令

运行全部单元测试：
```bash
cd /Users/dogbin/Documents/code/bin-ai-tech-aggregator/backend
python3 -m uv run pytest -q
```

---

## 9. 常用数据库查询

查看监控源：
```bash
python3 -m uv run python - <<'PY'
import sqlite3
c=sqlite3.connect("app.db")
print(c.execute("select id,type,value,is_active from monitor_sources order by id").fetchall())
PY
```

查看推送日志：
```bash
python3 -m uv run python - <<'PY'
import sqlite3
c=sqlite3.connect("app.db")
print(c.execute("select id,status,created_at from push_logs order by id desc limit 10").fetchall())
PY
```

查看推送明细（含热度/AI分）：
```bash
python3 -m uv run python - <<'PY'
import sqlite3
c=sqlite3.connect("app.db")
print(c.execute("select tweet_id,author_username,hotness,ai_score from push_log_items order by id desc limit 20").fetchall())
PY
```

查看通用资讯主表（推荐）：
```bash
python3 -m uv run python - <<'PY'
import sqlite3
c=sqlite3.connect("app.db")
print(c.execute("select id,platform,external_id,author_name,hotness,created_at from content_items order by id desc limit 20").fetchall())
PY
```

查看资讯 AI 分析缓存（推荐）：
```bash
python3 -m uv run python - <<'PY'
import sqlite3
c=sqlite3.connect("app.db")
print(c.execute("select content_item_id,ai_score,substr(summary,1,40),status,updated_at from content_ai_analyses order by id desc limit 20").fetchall())
PY
```

查看大模型调用日志（用于提示词优化）：
```bash
python3 -m uv run python - <<'PY'
import sqlite3
c=sqlite3.connect("app.db")
rows=c.execute("""
select id,source_id,model,status,substr(prompt_text,1,100),substr(response_text,1,100),created_at
from llm_call_logs
order by id desc
limit 10
""").fetchall()
for r in rows:
    print(r)
PY
```

---

## 10. 典型排障

1. `run-now` 返回 `total_sources=0`
- 原因：没有启用的监控源。
- 处理：插入或启用 `monitor_sources` 记录。

2. 飞书收不到消息
- 先跑第 5 节飞书直连 demo。
- 直连成功但业务失败：调用第 4 节 `/internal/webhook/test`。

3. 启动时报“重复 webhook_url 配置”
- 原因：`push_channels` 里有重复 webhook。
- 处理：去重，只保留一个相同 URL。

4. AI 失败
- 检查 `.env` 的 `ZAI_API_KEY` 与 `GLM_MODEL`。
- 查询 `llm_call_logs` 看 `error_message` 与原始返回。
