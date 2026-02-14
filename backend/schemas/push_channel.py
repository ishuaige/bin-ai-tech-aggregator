from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from models import ChannelPlatform


class PushChannelBase(BaseModel):
    platform: ChannelPlatform
    webhook_url: AnyHttpUrl
    name: str = Field(min_length=1, max_length=50)
    is_active: bool = True


class PushChannelCreate(PushChannelBase):
    pass


class PushChannelUpdate(BaseModel):
    platform: ChannelPlatform | None = None
    webhook_url: AnyHttpUrl | None = None
    name: str | None = Field(default=None, min_length=1, max_length=50)
    is_active: bool | None = None


class PushChannelResponse(PushChannelBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
