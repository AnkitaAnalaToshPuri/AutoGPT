import pydantic


class PushSubscriptionKeys(pydantic.BaseModel):
    p256dh: str
    auth: str


class PushSubscribeRequest(pydantic.BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys
    user_agent: str | None = None


class PushUnsubscribeRequest(pydantic.BaseModel):
    endpoint: str


class VapidPublicKeyResponse(pydantic.BaseModel):
    public_key: str
