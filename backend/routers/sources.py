from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models import MonitorSource, PushLog, SourceType
from routers.common import ok, page
from schemas import MonitorSourceCreate, MonitorSourceResponse, MonitorSourceUpdate

# 定义路由组 (Controller)
# prefix="/api/sources": 所有接口路径前缀
# tags=["sources"]: 用于 Swagger 文档分类
# 类似 Java Spring 的 @RequestMapping("/api/sources") + @Tag(name="sources")
router = APIRouter(prefix="/api/sources", tags=["sources"])


# POST /api/sources - 创建监控源
# payload: 请求体 JSON，自动映射为 MonitorSourceCreate 对象 (@RequestBody)
# db: 依赖注入获取数据库会话
@router.post("")
async def create_source(payload: MonitorSourceCreate, db: AsyncSession = Depends(get_db)) -> dict:
    # 1. 创建 ORM 对象
    row = MonitorSource(
        type=payload.type.value, # 枚举转字符串
        value=payload.value,
        is_active=payload.is_active,
        remark=payload.remark,
    )
    
    # 2. 添加到会话 (EntityManager.persist)
    db.add(row)
    
    # 3. 提交事务 (Transaction.commit)
    await db.commit()
    
    # 4. 刷新对象，获取自动生成的 ID (EntityManager.refresh)
    await db.refresh(row)
    
    # 5. 返回 DTO
    # model_validate: 从 ORM 对象创建 Pydantic 对象
    # model_dump: 转为字典
    return ok(MonitorSourceResponse.model_validate(row).model_dump())


# GET /api/sources - 获取监控源列表 (分页)
@router.get("")
async def list_sources(
    # Query 参数: ?page=1&page_size=20
    # alias="page": URL 参数名叫 page，代码里叫 page_no
    page_no: int = Query(default=1, alias="page", ge=1), # ge=1: >= 1
    page_size: int = Query(default=20, ge=1, le=100),    # le=100: <= 100
    type: SourceType | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # 构造查询语句 (Criteria API / QueryDSL)
    stmt = select(MonitorSource)
    count_stmt = select(func.count(MonitorSource.id))
    
    # 动态拼接 WHERE 条件
    if type is not None:
        stmt = stmt.where(MonitorSource.type == type.value)
        count_stmt = count_stmt.where(MonitorSource.type == type.value)
    if is_active is not None:
        stmt = stmt.where(MonitorSource.is_active == is_active)
        count_stmt = count_stmt.where(MonitorSource.is_active == is_active)

    # 执行 Count 查询
    # scalar_one(): 获取单个标量结果
    total = (await db.execute(count_stmt)).scalar_one()
    
    # 执行分页查询
    # offset/limit: MySQL LIMIT offset, limit
    stmt = stmt.order_by(MonitorSource.id.desc()).offset((page_no - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    
    # 转为 DTO 列表
    items = [MonitorSourceResponse.model_validate(row).model_dump() for row in rows]
    
    return page(items=items, total=total, page_no=page_no, page_size=page_size)


# PUT /api/sources/{source_id} - 更新监控源
@router.put("/{source_id}")
async def update_source(source_id: int, payload: MonitorSourceUpdate, db: AsyncSession = Depends(get_db)) -> dict:
    # 先查出来
    row = await db.get(MonitorSource, source_id)
    if row is None:
        # 抛出 404 异常
        raise HTTPException(status_code=404, detail="source_not_found")

    # exclude_unset=True: 只获取前端传了的字段，没传的忽略
    updates = payload.model_dump(exclude_unset=True)
    
    # 手动更新字段
    for key, value in updates.items():
        if key == "type" and value is not None:
             # 枚举特殊处理
            setattr(row, key, value.value)
        else:
            # 反射赋值
            setattr(row, key, value)

    await db.commit()
    await db.refresh(row)
    return ok(MonitorSourceResponse.model_validate(row).model_dump())


# DELETE /api/sources/{source_id} - 删除监控源
@router.delete("/{source_id}")
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    row = await db.get(MonitorSource, source_id)
    if row is None:
        return ok({"deleted": False, "reason": "source_not_found"})

    # 检查是否有依赖数据 (外键约束)
    # 如果有日志关联，不允许物理删除
    log_count = (await db.execute(select(func.count(PushLog.id)).where(PushLog.source_id == source_id))).scalar_one()
    if log_count > 0:
        raise HTTPException(status_code=409, detail="source_has_logs_cannot_delete")

    await db.delete(row)
    await db.commit()
    return ok({"deleted": True, "id": source_id})
