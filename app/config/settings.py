from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    LARK_APP_ID: str = ""
    LARK_APP_SECRET: str = ""
    LARK_BITABLE_APP_TOKEN: str = ""
    ZHIPUAI_API_KEY: str = ""
    AI_MODEL: str = "glm-5v-turbo"
    PORT: int = 3000
    ENV: str = "development"
    LOG_LEVEL: str = "info"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
