from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    PROVISIONING_TOKEN: str
    CRYPTO_KEY: str
    DEDUP_WINDOW_SECONDS: int = 60


settings = Settings()
