# 🛠️ 技术设计与实现方案：AI 资讯监控与推送系统 (v1.0)

## 1. 架构概览 (Architecture Overview)
本项目采用前后端分离的现代化 Web 架构。核心业务流为一个典型的 ETL（提取-转换-加载）数据管道：后台通过异步任务拉取推特/RSS 数据，交由 LLM 进行清洗和总结，存入本地数据库，并通过 Webhook 实时分发。前端提供可视化的管理看板。



## 2. 核心技术栈选型 (Technology Stack)

### 2.1 后端引擎 
* **运行环境与依赖管理**：Python 3.10+ / `uv`
* **Web 框架**：`FastAPI` (全异步支持，内置 Swagger API 文档)
* **数据校验**：`Pydantic v2` (基于类型提示的严格请求/响应校验)
* **ORM 与数据库**：`SQLAlchemy 2.0` (AsyncSession 异步模式) + `SQLite`
* **网络请求**：`httpx` (支持 `async/await` 的高性能 HTTP 客户端)
* **任务调度**：`APScheduler` (后台定时任务引擎)
* **AI 交互**：`openai` (官方 Python SDK)

### 2.2 前端看板 
* **核心框架**：Node.js 22 / `Vue 3` (Composition API)
* **构建工具**：`Vite`
* **UI 组件库**：`Element Plus`
* **网络与路由**：`Axios` + `Vue Router 4`

---

## 3. 数据库 ER 模型设计 (Database Schema)

系统底层由三张核心数据表支撑，采用下划线命名规范。



### 3.1 监控源配置表 (`monitor_sources`)
用于持久化设定的抓取目标。
| 字段名 | 类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | Primary Key, Auto Increment | 主键 |
| `type` | String(20) | Not Null | 枚举：`'author'`(博主) 或 `'keyword'`(关键字) |
| `value` | String(100) | Not Null | 目标值 (如 `karpathy`) |
| `is_active`| Boolean | Default `True` | 是否启用该抓取源 |
| `remark` | String(255)| Nullable | 备注说明 |

### 3.2 推送渠道配置表 (`push_channels`)
用于持久化 Webhook 机器人信息。
| 字段名 | 类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | Primary Key, Auto Increment | 主键 |
| `platform` | String(20) | Not Null | 平台枚举 (如 `'wechat'`) |
| `webhook_url`| String(255)| Not Null | 机器人完整调用地址 |
| `name` | String(50) | Not Null | 渠道命名 (如 `前端技术早报`) |
| `is_active`| Boolean | Default `True` | 是否启用该推送渠道 |

### 3.3 推送历史日志表 (`push_logs`)
用于沉淀处理后的数据，支持前端大盘展示与追溯。
| 字段名 | 类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | Primary Key, Auto Increment | 主键 |
| `source_id`| Integer | Foreign Key (`monitor_sources.id`) | 关联的源 ID |
| `raw_content`| Text | Nullable | 抓取到的原始文本 |
| `ai_summary` | Text | Nullable | AI 生成的 Markdown 摘要 |
| `status` | String(20) | Not Null | 执行状态 (`'success'`, `'failed'`) |
| `created_at` | DateTime | Default `now()` | 记录创建时间 |

---

## 4. 系统目录分层与核心模块 (Directory Structure & Core Modules)

为保证代码的高可维护性和扩展性，后端代码严格遵循以下分层架构：

* **`models/` (数据持久层)**：使用 SQLAlchemy 定义数据库表结构模型。
* **`schemas/` (数据交互层)**：使用 Pydantic 定义 API 的请求体 (Request) 和响应体 (Response)，进行严格的数据校验。
* **`services/` (业务逻辑层)**：
    * `crawler_service.py`: 负责异步拉取推特/RSS等外部数据源。
    * `llm_service.py`: 负责构建 Prompt 并调用大模型 API 生成结构化摘要。
    * `notify_service.py`: 负责组装 Markdown 消息体并推送到指定的 Webhook 渠道。
* **`routers/` (API 路由层)**：使用 FastAPI 暴露 RESTful 接口，按业务模块划分路由。

---

## 5. 项目交付阶段规划 (Project Milestones)

* **Phase 1: 核心引擎与底层基础 (Core Engine & Infrastructure)**
  * 完成项目运行环境的初始化与依赖锁定。
  * 实现基础的异步数据抓取、大模型 API 接入与 Webhook 消息推送核心链路。
* **Phase 2: 服务化与数据持久化 (API & Data Persistence)**
  * 完成 SQLite 数据库及数据表的设计与自动构建。
  * 封装标准的 RESTful API，实现监控配置与推送渠道的动态 CRUD。
* **Phase 3: 前端看板与自动化调度 (Dashboard & Automation)**
  * 搭建 Vue 3 前端管理后台，对接后端 API 实现数据可视化与交互。
  * 引入后台定时任务调度器 (Scheduler)，实现每日自动化信息聚合与推送闭环。