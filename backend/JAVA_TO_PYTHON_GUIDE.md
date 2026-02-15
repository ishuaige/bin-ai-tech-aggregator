# ☕️ Java 程序员的 Python 极速入门指南 (基于本项目)

欢迎！如果你熟悉 Java (Spring Boot)，那么恭喜你，你已经掌握了 Python 开发 80% 的概念。这份指南将结合本项目的实际代码，带你通过对比，快速上手 Python 开发。

---

## 🗺️ 核心映射图谱

先建立概念映射，让你感到亲切：

| 概念 | Java (Spring Boot) | Python (FastAPI + SQLAlchemy) | 项目代码示例 |
| :--- | :--- | :--- | :--- |
| **包管理** | Maven (`pom.xml`) | uv / pip (`pyproject.toml`) | [`pyproject.toml`](./pyproject.toml) |
| **入口** | `Application.java` (`main` 方法) | `main.py` (`app = FastAPI(...)`) | [`main.py`](./main.py) |
| **Bean/DTO**| POJO + Lombok (`@Data`) | Pydantic Models | [`schemas/api.py`](./schemas/api.py) |
| **Web层** | `@RestController` + `@RequestMapping` | `APIRouter` + `@router.get` | [`routers/sources.py`](./routers/sources.py) |
| **ORM** | JPA / Hibernate (`@Entity`) | SQLAlchemy (`class Model(Base)`) | [`models/monitor_source.py`](./models/monitor_source.py) |
| **Service**| `@Service` | 普通类或模块 | [`services/llm_service.py`](./services/llm_service.py) |
| **依赖注入**| `@Autowired` | `Depends(...)` | [`routers/sources.py`](./routers/sources.py) |
| **异步** | `CompletableFuture` / `@Async` | `async` / `await` | (全项目通用) |

---

## 🚀 第一步：语法习惯大扫除 (Syntax Detox)

在看代码前，先忘掉 Java 的一些肌肉记忆：

1.  **分号消失了** 🚫`;`：Python 不需要分号结尾。
2.  **大括号消失了** 🚫`{}`：代码块完全靠 **缩进** (通常是 4 个空格)。**缩进不对，程序直接报错！**
3.  **类型在后面**：Java `String name` -> Python `name: str`。
4.  **`new` 消失了**：创建对象直接调类名 `User()`，不用 `new User()`。
5.  **`null` 变身**：Java 的 `null` 在 Python 里叫 `None`。
6.  **`this` 显形**：Java 的 `this` 是隐式的，Python 类方法第一个参数必须写 `self`。

---

## 🔍 第二步：从 DTO 开始 (Schemas)

Java 中我们定义 DTO/VO 用于前后端数据交互。Python 中我们使用 **Pydantic** 库，它比 Java Bean 更强大，自带校验。

👉 **打开代码**: [`backend/schemas/api.py`](./schemas/api.py)

```python
# Java: public class ApiResponse<T> { ... }
class ApiResponse(BaseModel):
    code: int = 0             # 字段: 类型 = 默认值
    message: str = "ok"
    # Union Type: 类似 Java 的 Object 或泛型，但更明确
    data: dict | list | str | int | float | bool | None = None
```

*心得：不需要写 Getter/Setter/ToString，继承 `BaseModel` 全都有了。*

---

## 🗄️ 第三步：数据库实体 (Models)

Java 用 Hibernate/JPA 的 `@Entity`，Python 用 **SQLAlchemy**。

👉 **打开代码**: [`backend/models/monitor_source.py`](./models/monitor_source.py)

```python
# Java: @Entity @Table(name="monitor_sources")
class MonitorSource(Base):
    __tablename__ = "monitor_sources"

    # Java: @Id @GeneratedValue
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Java: @Column(nullable = false)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
```

*心得：结构非常相似，只是注解变成了属性赋值。*

---

## 🌐 第四步：写一个接口 (Routers)

这是你最熟悉的部分。看看如何写一个 CRUD 接口。

👉 **打开代码**: [`backend/routers/sources.py`](./routers/sources.py)

```python
# Java: @RestController @RequestMapping("/api/sources")
router = APIRouter(prefix="/api/sources", tags=["sources"])

# Java: @GetMapping
@router.get("")
async def list_sources(
    # Java: @RequestParam(defaultValue = "1") int page
    page_no: int = Query(default=1, alias="page", ge=1),
    
    # Java: @Autowired EntityManager db
    # FastAPI 的依赖注入非常简洁，直接在参数里写 Depends
    db: AsyncSession = Depends(get_db),
):
    # SQLAlchemy 2.0 查询风格 (类似 JPA Criteria 或 QueryDSL)
    stmt = select(MonitorSource)
    # Java: .where(cb.equal(root.get("type"), type))
    stmt = stmt.where(MonitorSource.type == type.value)
    
    # 执行查询 (异步 await)
    rows = (await db.execute(stmt)).scalars().all()
    
    return page(...)
```

---

## ⚡️ 第五步：理解 `async` / `await`

这是 Python 后端性能的关键，也是和 Java 最大的不同点。

*   **Java**: 传统的 Servlet 是 **多线程阻塞模型** (Thread-per-request)。
*   **Python (FastAPI)**: **单线程协程模型** (Event Loop)。

**核心规则**：
1.  **定义**：耗时操作（查库、调API）的函数前加 `async`。
2.  **调用**：调用 `async` 函数时，必须加 `await`。
    *   ✅ `result = await db.execute(...)` (等待结果，但释放 CPU 给别的请求用)
    *   ❌ `result = db.execute(...)` (这就错了！你会得到一个 `Coroutine` 对象，而不是结果)

---

## 🎓 推荐阅读路径

建议按照以下顺序阅读本项目代码，逐步建立信心：

1.  🟢 **入门**: [`schemas/api.py`](./schemas/api.py) & [`schemas/crawler.py`](./schemas/crawler.py)
    *   先看数据结构，最简单，建立业务概念。
2.  🟢 **基础**: [`models/monitor_source.py`](./models/monitor_source.py)
    *   看看数据库表是怎么定义的。
3.  🟡 **核心**: [`routers/sources.py`](./routers/sources.py)
    *   **重点阅读！** 这是一个标准的 CRUD 实现，包含了你日常开发 80% 的场景。
4.  🔴 **进阶**: [`services/llm_service.py`](./services/llm_service.py)
    *   看看如何封装复杂的业务逻辑，学习如何调用第三方 API，如何做异常处理和重试。

---

*Happy Coding! 把 Python 当作 "可执行的伪代码" (Executable Pseudocode) 去写就好，它没有那么多条条框框。*
