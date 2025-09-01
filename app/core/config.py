from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    DESCOPE_PROJECT_ID: str = Field(..., alias="DESCOPE_PROJECT_ID")
    DESCOPE_MANAGEMENT_KEY: str | None = Field(None, alias="DESCOPE_MANAGEMENT_KEY")
    DESCOPE_BASE_URL: str = Field("https://api.descope.com", alias="DESCOPE_BASE_URL")

    ALLOWED_CORS_ORIGINS: str = Field("*", alias="ALLOWED_CORS_ORIGINS")
    LOG_LEVEL: str = Field("INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(env_file=".env", populate_by_name=True)

    @property
    def cors_origins_list(self) -> list[str]:
        if self.ALLOWED_CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_CORS_ORIGINS.split(",")]

settings = Settings()
