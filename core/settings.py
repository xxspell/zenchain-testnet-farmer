from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class EnvSettings(BaseSettings):
    console_log: str = "INFO"

    @field_validator('console_log')
    def validate_console_log(cls, value):
        value.upper()
        valid_types = ["INFO", "DEBUG", "WARNING"]

        if value not in valid_types:
            raise ValueError(f"Invalid console log type message: '{value}'. Must be one of: {', '.join(valid_types)}")
        return value


    class Config:
        env_file = ".env"
        case_sensitive = False



class AppSettings(BaseSettings):
    pass




class Settings(BaseSettings):
    env: EnvSettings = EnvSettings()
    app: AppSettings = AppSettings()


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
