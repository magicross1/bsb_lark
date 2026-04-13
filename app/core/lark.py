import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *

from app.config.app_settings import settings

_client: lark.Client | None = None


def get_lark_client() -> lark.Client:
    global _client
    if _client is None:
        _client = (
            lark.Client.builder()
            .app_id(settings.LARK_APP_ID)
            .app_secret(settings.LARK_APP_SECRET)
            .log_level(lark.LogLevel.DEBUG if settings.ENV == "development" else lark.LogLevel.INFO)
            .build()
        )
    return _client
