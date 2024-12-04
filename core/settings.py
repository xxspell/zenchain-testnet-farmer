from pydantic_settings import BaseSettings
from functools import lru_cache


class EnvSettings(BaseSettings):



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
