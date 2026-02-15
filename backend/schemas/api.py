from __future__ import annotations

from pydantic import BaseModel


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int


class PageResult(BaseModel):
    items: list
    meta: PageMeta


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: dict | list | str | int | float | bool | None = None
