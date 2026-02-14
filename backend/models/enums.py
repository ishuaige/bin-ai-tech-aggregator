"""模型层与 Schema 层共用的枚举定义。"""

from enum import Enum


class SourceType(str, Enum):
    AUTHOR = "author"
    KEYWORD = "keyword"


class ChannelPlatform(str, Enum):
    WECHAT = "wechat"
    DINGTALK = "dingtalk"
    FEISHU = "feishu"


class PushStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
