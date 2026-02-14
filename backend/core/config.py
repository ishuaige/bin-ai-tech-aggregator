from functools import lru_cache

# pydantic_settings 是 Python 中非常流行的配置管理库
# 它可以自动读取环境变量、.env 文件，并进行类型转换和校验
from pydantic_settings import BaseSettings, SettingsConfigDict


# 定义配置类，继承自 BaseSettings
# 类似 Java Spring 的 @ConfigurationProperties + @Value
class Settings(BaseSettings):
    # 必填项：如果环境变量中没有 API_KEY，程序启动会报错
    API_KEY: str
    
    # 数据库连接串
    DB_URL: str

    # 选填项：有默认值
    APP_NAME: str = "AI Tech Aggregator Backend"
    APP_ENV: str = "development"

    # 配置元数据
    model_config = SettingsConfigDict(
        env_file=".env",           # 指定读取根目录下的 .env 文件
        env_file_encoding="utf-8", # 文件编码
        extra="ignore",            # 忽略 .env 中多余的字段，不报错
    )


# @lru_cache 是 Python 内置的缓存装饰器
# 作用：第一次调用 get_settings() 会创建 Settings 对象并读取文件
# 后续调用直接返回缓存的对象，避免重复读取文件，提高性能
# 类似 Java 的单例模式 (Singleton)
@lru_cache
def get_settings() -> Settings:
    return Settings()
