# TODO 清单：AI 技术资讯监控与推送系统

说明：
- 本清单依据 `docs/PRD.md` 与 `docs/TECH_DESIGN.md` 拆解。
- 每项任务均附带「验收标准」，完成后可直接打勾。

## Phase 2: 数据库与模型

- [x] 2.1 建立后端目录分层骨架（`models/`、`schemas/`、`services/`、`routers/`、`core/`、`db/`）
  验收标准：目录与 `__init__.py` 文件齐全，`main.py` 能正常导入各层模块。

- [x] 2.2 定义数据库连接与会话管理（SQLite + SQLAlchemy 2.0 AsyncEngine/AsyncSession）
  验收标准：提供 `get_db` 异步依赖；启动时能成功建立引擎；无同步阻塞 DB 调用。

- [x] 2.3 实现数据库初始化脚本（自动创建表）
  验收标准：执行初始化命令后成功生成 SQLite 文件，核心业务表（`monitor_sources`、`push_channels`、`content_items`、`content_ai_analyses`、`push_logs`）存在。

- [x] 2.4 定义 `monitor_sources` SQLAlchemy 模型
  验收标准：字段与设计文档一致（`id/type/value/is_active/remark`），约束生效。

- [x] 2.5 定义 `push_channels` SQLAlchemy 模型
  验收标准：字段与设计文档一致（`id/platform/webhook_url/name/is_active`），约束生效。

- [x] 2.6 定义 `push_logs` SQLAlchemy 模型及外键关系
  验收标准：字段与设计文档一致（`source_id/raw_content/ai_summary/status/created_at`），外键能关联 `monitor_sources.id`。

- [x] 2.7 补充模型枚举与索引（source type、platform、status）
  验收标准：非法枚举值写入时报错；常用查询字段建立索引并可在 SQLite schema 中看到。

- [x] 2.8 定义监控源 Pydantic Schema（Create/Update/Response）
  验收标准：请求校验覆盖必填项、长度、枚举；Swagger 中显示清晰字段说明。

- [x] 2.9 定义推送渠道 Pydantic Schema（Create/Update/Response）
  验收标准：`webhook_url` 格式校验有效；创建/更新请求可正确通过与拒绝。

- [x] 2.10 定义推送日志 Pydantic Schema（List/Detail）
  验收标准：返回结构与前端展示需求一致，时间字段序列化格式统一。

- [x] 2.11 增加数据库基础测试数据/seed 脚本
  验收标准：一条命令可写入示例 source/channel/log 数据，重复执行可控（不产生脏重复）。

- [x] 2.12 配置管理实现（`core/config.py`）
  验收标准：使用 `pydantic-settings` 读取 `.env` 文件；包含 `API_KEY`、`DB_URL` 等关键配置；程序启动时能校验必填项。

## Phase 3: 核心业务逻辑

- [x] 3.1 编写 `crawler_service`：基于 TwitterAPI.io 按博主抓取内容（author 模式）
  验收标准：调用 `get_user_last_tweets` 成功返回推文列表，并映射为统一 DTO（含 `tweet_id`、`url`、`text`、`published_at`）；默认仅保留最新 10 条（可配置）。

- [x] 3.2 编写 `crawler_service`：基于 TwitterAPI.io 按关键字抓取内容（keyword 模式）
  验收标准：调用 `tweet_advanced_search`（`query` + `queryType=Top`）返回推文列表，并映射为统一 DTO；查询语句支持 `min_faves` 阈值过滤；空结果与异常场景有明确返回。

- [x] 3.3 统一抓取结果 DTO（内部数据结构）
  验收标准：author/keyword 两种抓取均返回 `CrawlBatchResult(items: list[CrawlItem])`，后续服务无需分支适配。

- [x] 3.4 编写抓取去重与基础清洗逻辑
  验收标准：同一批次重复内容被去重；空文本与明显噪音文本被过滤。

- [x] 3.5 编写 `llm_service`：Prompt 模板与参数封装
  验收标准：给定抓取内容可生成稳定 prompt；要求输出 3-5 条中文 Markdown 要点。

- [x] 3.6 接入智谱 GLM SDK 异步调用并实现超时/重试
  验收标准：网络波动场景下可重试；超时后返回可追踪错误；async 代码中不出现同步阻塞调用。

- [x] 3.7 解析并校验 LLM 返回内容格式
  验收标准：结果为空、格式异常时可降级处理并记录失败原因。

- [x] 3.8 编写 `notify_service`：Webhook 消息组装（Markdown）
  验收标准：消息包含来源、摘要、时间等关键字段；可读性符合企业群通知场景。

- [x] 3.9 编写 `notify_service`：异步发送与错误处理
  验收标准：Webhook 200 视为成功；非 200 与网络失败记录错误并不中断其他渠道发送。

- [x] 3.10 实现单源执行编排（抓取 -> 总结 -> 推送 -> 记日志）
  验收标准：执行一次后 `push_logs` 新增记录，状态与结果一致。

- [x] 3.11 实现全局批处理编排（遍历启用 source）
  验收标准：仅处理 `is_active=true` 的监控源；批次完成后输出汇总统计（成功/失败数）。

- [x] 3.12 集成 APScheduler 定时任务（默认每日 08:30）
  验收标准：应用启动后注册任务成功；到时触发一次完整批处理链路。

- [x] 3.13 实现“手动立即执行”服务入口
  验收标准：调用后即时触发批处理，不影响定时任务的下次执行。

- [x] 3.14 增加日志与可观测性（结构化日志 + request id）
  验收标准：抓取、LLM、推送、DB 写入关键步骤均可在日志中追踪。

- [x] 3.15 补齐核心服务单元测试（crawler/llm/notify/orchestrator）
  验收标准：关键路径和失败路径均有测试；测试通过率 100%。

- [x] 3.16 建立通用资讯数据模型（`content_items` + `content_ai_analyses`）
  验收标准：抓取结果先落 `content_items`，AI 分析结果落 `content_ai_analyses`，推送日志仅作为历史记录。

- [x] 3.17 优化 AI 调用为批量分析
  验收标准：缺失缓存资讯按批次调用 GLM（非逐条请求），批大小可配置，调用耗时与次数明显下降。

## Phase 4: API 接口

- [ ] 4.1 设计统一 API 响应结构与错误码规范
  验收标准：成功/失败响应格式一致，前端可基于 code/message/data 统一处理。

- [ ] 4.2 实现监控源新增接口 `POST /api/sources`
  验收标准：可创建 author/keyword 源；参数非法时返回明确校验错误。

- [ ] 4.3 实现监控源列表接口 `GET /api/sources`
  验收标准：支持分页与基础筛选（type/is_active）。

- [ ] 4.4 实现监控源更新接口 `PUT /api/sources/{id}`
  验收标准：可更新 value/remark/is_active；不存在 id 返回 404。

- [ ] 4.5 实现监控源删除接口 `DELETE /api/sources/{id}`
  验收标准：删除后列表不可见；有关联历史日志时策略明确（软删或限制删）。

- [ ] 4.6 实现推送渠道新增接口 `POST /api/channels`
  验收标准：可创建 channel；`webhook_url` 非法时被拒绝。

- [ ] 4.7 实现推送渠道列表接口 `GET /api/channels`
  验收标准：支持分页与启停筛选；返回字段满足配置页面展示。

- [ ] 4.8 实现推送渠道更新接口 `PUT /api/channels/{id}`
  验收标准：可更新 name/platform/webhook_url/is_active；无效 id 返回 404。

- [ ] 4.9 实现推送渠道删除接口 `DELETE /api/channels/{id}`
  验收标准：删除逻辑可重复调用（幂等行为明确），返回码符合规范。

- [ ] 4.10 实现执行日志列表接口 `GET /api/logs`
  验收标准：支持按日期、关键字、状态筛选，并提供分页总数。

- [ ] 4.11 实现执行日志详情接口 `GET /api/logs/{id}`
  验收标准：返回 `raw_content` 与 `ai_summary`，便于前端历史墙详情查看。

- [ ] 4.12 实现手动触发接口 `POST /api/jobs/run-now`
  验收标准：触发后立即返回受理结果；后台任务实际开始执行并产生日志。

- [ ] 4.13 实现仪表盘统计接口 `GET /api/dashboard/overview`
  验收标准：返回今日抓取量、最近执行状态、基础消耗估算字段。

- [ ] 4.14 增加健康检查接口 `GET /health` 与 `GET /ready`
  验收标准：`health` 表示进程存活；`ready` 能验证数据库可用性。

- [ ] 4.15 完善 Swagger 文档、示例请求与错误响应示例
  验收标准：打开 `/docs` 可直接调试所有核心接口，字段说明完整。

- [ ] 4.16 编写 API 集成测试（含数据库隔离）
  验收标准：关键 CRUD + run-now + logs 查询均自动化通过。

## Phase 5: 前端页面

- [ ] 5.1 初始化前端项目结构与基础依赖（Vue3 + Vite + Element Plus + Vue Router + Axios + `markdown-it`/`marked`）
  验收标准：`frontend` 可启动，路由可切换，基础布局正常渲染。

- [ ] 5.2 建立 API 请求层（Axios 实例、拦截器、错误处理）
  验收标准：统一处理 loading、错误提示与后端响应结构。

- [ ] 5.3 实现全局布局（侧边导航 + 顶栏 + 内容区）
  验收标准：包含 Dashboard、Settings、History 三个入口并可访问。

- [ ] 5.4 实现 Dashboard 页面：今日抓取量/最近执行状态/API 消耗估算卡片
  验收标准：页面加载后正确展示 `overview` 接口数据，空态可用。

- [ ] 5.5 实现 Dashboard “立即执行”按钮与状态反馈
  验收标准：点击后调用 run-now 接口；成功/失败均有可见反馈。

- [ ] 5.6 实现 Settings 页面：监控源列表与筛选
  验收标准：支持分页、按类型与启停状态筛选。

- [ ] 5.7 实现 Settings 页面：监控源新增/编辑弹窗表单
  验收标准：表单校验覆盖必填与格式；提交后列表自动刷新。

- [ ] 5.8 实现 Settings 页面：监控源启停开关与删除操作
  验收标准：切换状态实时生效；删除需二次确认并正确更新 UI。

- [ ] 5.9 实现 Settings 页面：推送渠道列表与筛选
  验收标准：展示 name/platform/webhook/is_active，交互与监控源一致。

- [ ] 5.10 实现 Settings 页面：推送渠道新增/编辑/删除
  验收标准：Webhook URL 校验有效；提交成功后即时反映到列表。

- [ ] 5.11 实现 History 页面：日志列表分页与筛选（日期/关键字/状态）
  验收标准：查询条件可组合；翻页与筛选联动正确。

- [ ] 5.12 实现 History 页面：日志详情抽屉（原文 + AI 摘要）
  验收标准：点击记录可查看完整详情；Markdown 语法（如 `**加粗**`、`- 列表`）能被解析为正确的 HTML 标签并渲染。

- [ ] 5.13 实现通用空态、加载态、错误态组件
  验收标准：各页面在无数据、请求中、请求失败时均有统一表现。

- [ ] 5.14 前端联调与端到端验收
  验收标准：从新增 source/channel 到手动执行再到历史查看，全链路可操作且结果正确。
