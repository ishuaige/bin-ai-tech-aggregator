# 🛠️ 技术设计与实现方案：AI 资讯监控与推送系统 (v1.1)

## 1. 架构概览 (Architecture Overview)
本项目采用前后端分离架构。后端核心是异步 ETL 管道：
1. 按监控源抓取资讯（当前已接入 TwitterAPI.io）。
2. 进行去重、清洗与热度评分。
3. 将原始资讯落库到通用内容主表。
4. 调用 GLM 对缺失项做批量分析并缓存。
5. 生成摘要并推送到 Webhook 渠道。
6. 记录推送执行日志与 LLM 调用日志。

## 2. 核心技术栈选型 (Technology Stack)

### 2.1 后端引擎
- 运行环境与依赖管理：Python 3.10+ / `uv`
- Web 框架：`FastAPI`
- 数据校验：`Pydantic v2`
- 配置管理：`pydantic-settings`
- ORM 与数据库：`SQLAlchemy 2.0` (AsyncSession) + `SQLite`
- 网络请求：`httpx`
- 任务调度：`APScheduler`
- AI 交互：智谱 GLM（`zai-sdk`）

### 2.2 前端看板
- 核心框架：Node.js 22 / `Vue 3`
- 构建工具：`Vite`
- UI 组件库：`Element Plus`
- 网络与路由：`Axios` + `Vue Router 4`

---

## 3. 数据库模型设计 (Database Schema)

### 3.1 监控源配置表 (`monitor_sources`)
- 作用：管理抓取目标（博主/关键字）。
- 关键字段：`id`, `type`, `value`, `is_active`, `remark`。

### 3.2 推送渠道配置表 (`push_channels`)
- 作用：管理企业微信/飞书/钉钉 Webhook。
- 关键字段：`id`, `platform`, `webhook_url`, `name`, `is_active`。

### 3.3 通用资讯主表 (`content_items`)
- 作用：沉淀抓取到的原始资讯主数据，支持未来多平台扩展。
- 关键字段：
  - `platform`：平台标识（当前 `twitter`）
  - `source_type`：来源类型（如 `author_timeline` / `tweet_advanced_search`）
  - `external_id`：第三方内容 ID
  - `author_name`, `url`, `title`, `content_text`
  - `content_hash`：正文哈希（用于判断 AI 缓存是否失效）
  - `published_at`, `raw_payload`, `hotness`

### 3.4 资讯 AI 分析表 (`content_ai_analyses`)
- 作用：每条资讯对应一条最新 AI 分析结果。
- 关键字段：
  - `content_item_id`（唯一）
  - `ai_score`, `summary`, `model`
  - `content_hash`（与 `content_items` 对齐）
  - `prompt_text`, `response_text`, `status`, `failure_reason`

### 3.5 推送历史日志表 (`push_logs`)
- 作用：记录每次执行结果（成功/失败、摘要、时间）。

### 3.6 推送明细表 (`push_log_items`)
- 作用：记录每次推送批次中的资讯明细（便于前端历史展示）。

### 3.7 大模型调用日志表 (`llm_call_logs`)
- 作用：记录每次 LLM 调用请求与响应，支持提示词优化分析。

---

## 4. 核心业务规则

### 4.1 抓取策略
- `author` 模式：抓取用户最近内容，默认仅取最新 `10` 条（`AUTHOR_FETCH_LIMIT`）。
- `keyword` 模式：使用 `tweet_advanced_search` + `queryType=Top`。
- 关键字查询会附加点赞阈值：`min_faves:{KEYWORD_MIN_LIKES}`，并在本地再次做 likeCount 阈值过滤。

### 4.2 AI 分析策略
- 先查 `content_ai_analyses` 缓存（通过 `content_hash` 判断是否可复用）。
- 仅对缺失或内容变更项调用 GLM。
- 采用批量分析，按 `LLM_ANALYZE_BATCH_SIZE` 分批调用，降低请求次数与耗时。

### 4.3 推送策略
- 飞书：仅发送热度前 10 条资讯。
- 其他渠道：按传入列表发送。
- 推送消息包含标题、来源、AI 评分、标签、发布时间、AI 提炼。

---

## 5. 系统目录分层与核心模块 (Directory Structure & Core Modules)
- `models/`：SQLAlchemy 模型定义。
- `schemas/`：Pydantic 请求/响应与内部 DTO。
- `services/`：核心业务逻辑。
  - `crawler_service.py`：抓取外部资讯。
  - `content_filter_service.py`：去重与清洗。
  - `scoring_service.py`：热度评分。
  - `llm_service.py`：GLM 调用、格式解析、批量分析。
  - `pipeline_service.py`：抓取到推送的编排。
  - `notify_service.py`：Webhook 消息组装与发送。
  - `scheduler_service.py`：定时调度。
- `db/`：数据库引擎、会话与建表初始化。
- `main.py`：应用生命周期、健康检查、内部调试入口。

---

## 6. 项目阶段状态（当前）
- Phase 2：已完成（数据库与配置管理）。
- Phase 3：核心链路已完成并持续优化（批量 AI、缓存复用、多渠道推送）。
- Phase 4/5：待继续推进 API 完整化与前端页面联调。
