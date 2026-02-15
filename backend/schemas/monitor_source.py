from pydantic import BaseModel, ConfigDict, Field

from models import SourceType


# MonitorSourceBase: 基础 Schema，包含公共字段
# 这种分层定义 (Base -> Create -> Response) 是 Pydantic 的常见模式
# 类似 Java DTO 的继承关系
class MonitorSourceBase(BaseModel):
    type: SourceType # 枚举类型
    # min_length, max_length: 自动校验规则，类似 @Size(min=1, max=100)
    value: str = Field(min_length=1, max_length=100)
    is_active: bool = True
    remark: str | None = Field(default=None, max_length=255)


# 创建时的 Schema (继承自 Base)
class MonitorSourceCreate(MonitorSourceBase):
    pass


# 更新时的 Schema
# 所有字段都是可选的 (None)，因为更新时可能只改其中一个字段
class MonitorSourceUpdate(BaseModel):
    type: SourceType | None = None
    value: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None
    remark: str | None = Field(default=None, max_length=255)


# 响应时的 Schema (返回给前端)
# 包含数据库 ID，且允许从 ORM 对象转换
class MonitorSourceResponse(MonitorSourceBase):
    id: int

    # ConfigDict(from_attributes=True):
    # 允许 Pydantic 直接从 ORM 对象（如 MonitorSource 实例）读取数据
    # 以前的版本叫 orm_mode = True
    # 这样就可以直接写 MonitorSourceResponse.model_validate(db_obj)
    model_config = ConfigDict(from_attributes=True)
