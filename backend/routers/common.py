from __future__ import annotations


# 定义通用 API 响应包装函数
# 类似 Java 中的 R.ok(data) 或 Result.success(data)
def ok(data=None, message: str = "ok") -> dict:
    return {"code": 0, "message": message, "data": data}


# 定义分页响应包装函数
# 类似 Java 中的 PageResult<T>
def page(items: list, total: int, page_no: int, page_size: int) -> dict:
    return ok(
        data={
            "items": items,
            "meta": {
                "page": page_no,
                "page_size": page_size,
                "total": total,
            },
        }
    )
