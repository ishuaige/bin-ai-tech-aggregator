# 🐍 后端代码规范指南 (Python / FastAPI)

## 1. 代码格式化与代码检查 (Linting & Formatting)
本项目抛弃传统的 Flake8，全面拥抱现代化的极速工具链：
* **代码格式化**：统一使用 `Black`，行宽限制设定为 `88` 个字符。所有代码提交前必须经过 Black 格式化。
* **代码检查与导包排序**：统一使用 `Ruff`（基于 Rust 编写，速度极快）。它同时替代了 Pylint 和 isort，负责检查未使用的变量并自动将 `import` 语句按系统库、第三方库、本地模块的顺序分组排序。

## 2. 命名规范 (Naming Conventions)
* **变量、函数与方法**：强制使用下划线命名法 (`snake_case`)。例如：`fetch_twitter_data()`。
* **类名**：强制使用大驼峰命名法 (`PascalCase`)。例如：`MonitorConfig`, `CrawlerService`。
* **常量**：强制使用全大写加下划线 (`UPPER_SNAKE_CASE`)。例如：`DEFAULT_TIMEOUT = 30`。
* **私有属性/方法**：Python 没有真正的私有修饰符，内部使用的变量或方法约定以单下划线开头。例如：`_parse_raw_html()`。

## 3. 类型提示 (Type Hints)
本项目强依赖 FastAPI 和 Pydantic，**强制要求所有函数、方法签名必须包含类型注解**。
* 入参和返回值必须明确类型，如果没有返回值标注为 `-> None`。
* 复杂结构使用 `typing` 模块中的 `List`, `Dict`, `Optional`, `Any` 等。
* **示例**：
  ```python
  async def get_summary(raw_text: str, max_length: int = 100) -> Optional[str]:
      pass
  
# ⚡ 前端代码规范指南 (Vue 3 / Vite)

## 1. 代码格式化与检查 (Linting & Formatting)
* **代码格式化**：统一使用 `Prettier`。配置单引号优先 (`singleQuote: true`)，句尾不强制加分号 (`semi: false`)，缩进为 2 个空格。
* **代码检查**：统一使用 `ESLint`，并继承 Vue 官方推荐的 `plugin:vue/vue3-recommended` 规则集。

## 2. Vue 3 专属规范 (Composition API)
* **脚本编写**：强制使用 `<script setup>` 语法糖，严禁混用传统的 Options API（如 `data()`, `methods`, `computed` 选项）。
* **响应式状态**：
  * 简单基础类型数据统一使用 `ref()`。
  * 复杂对象（如表单数据实体）统一使用 `reactive()`。
* **组合式函数 (Composables)**：所有复用的业务逻辑必须抽离到 `src/composables` 目录下，并以 `use` 开头命名（例如：`useMonitor()`, `useFormatter()`）。

## 3. 文件与组件命名规范 (Naming Conventions)
* **组件文件**：单文件组件（`.vue` 文件）强制使用大驼峰命名法 (`PascalCase`)。例如：`DashboardCard.vue`, `MonitorTable.vue`。
* **组件使用**：在模板（Template）中引入和使用自定义组件时，强制使用大驼峰闭合标签。例如：`<DashboardCard />`。
* **普通文件与变量**：普通 `.js` / `.ts` 文件、函数、变量，统一使用小驼峰命名法 (`camelCase`)。例如：`request.js`, `fetchData()`。

## 4. API 请求与网络层规范 (Network Requests)
* **统一封装**：严禁在 Vue 组件内部直接调用原生的 `fetch` 或 `axios.get`。所有的接口调用必须封装在 `src/api/` 目录下（如 `src/api/monitor.js`）。
* **拦截器**：必须配置 Axios 全局拦截器。
  * 请求拦截器：负责附加 Token 或统一的 Header。
  * 响应拦截器：负责全局拦截 HTTP 错误码（如 401, 500），并统一调用 Element Plus 的 `ElMessage` 弹出错误提示，组件内部只处理成功的业务逻辑。

## 5. CSS/样式规范 (Styling)
* **作用域隔离**：所有的组件样式必须添加 `scoped` 属性 `<style scoped>`，防止样式全局污染。
* **UI 库覆盖**：如需覆盖 Element Plus 的默认组件样式，必须使用深度选择器 `:deep()`，而不是去除 `scoped` 或直接写全局 CSS。