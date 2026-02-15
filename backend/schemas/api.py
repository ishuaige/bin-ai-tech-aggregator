from __future__ import annotations

# Pydantic 是 Python 中最强大的数据验证和序列化库
# 它可以自动将 JSON 请求体转换为 Python 对象，并进行类型检查
# 类似 Java 的 Jackson + Bean Validation (JSR 380)
from pydantic import BaseModel


# 定义分页元数据
class PageMeta(BaseModel):
    page: int       # 当前页码
    page_size: int  # 每页大小
    total: int      # 总记录数


# 定义通用分页结果
# 类似 Java 的 Page<T>
class PageResult(BaseModel):
    items: list     # 数据列表
    meta: PageMeta  # 分页信息


# 定义通用 API 响应结构
# 类似 Java 的 Result<T> 或 ApiResponse<T>
class ApiResponse(BaseModel):
    code: int = 0             # 业务状态码，0 表示成功
    message: str = "ok"       # 提示信息
    # data 字段可以是多种类型，类似 Java 的 Object 或泛型 T
    # dict | list ... 是 Python 3.10+ 的联合类型写法 (Union Type)
    data: dict | list | str | int | float | bool | None = None
