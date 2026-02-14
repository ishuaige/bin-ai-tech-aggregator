# SQLAlchemy 是 Python 最流行的 ORM 框架，地位等同于 Java 的 Hibernate/JPA
from sqlalchemy.orm import DeclarativeBase


# 定义 ORM 的基类
# 所有的数据表模型（Model）都必须继承这个 Base 类
# 它的作用类似 JPA 的 @Entity 注解机制，用于注册和管理所有实体
class Base(DeclarativeBase):
    pass
