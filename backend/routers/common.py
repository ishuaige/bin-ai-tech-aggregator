from __future__ import annotations


def ok(data=None, message: str = "ok") -> dict:
    return {"code": 0, "message": message, "data": data}


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
