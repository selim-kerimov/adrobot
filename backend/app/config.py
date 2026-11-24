from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://adrobot:adrobot@localhost:5433/adrobot"
    keitaro_url: str = ""
    keitaro_api_key: str = ""


settings = Settings()
