from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class EnvSettings(BaseSettings):
    console_log: str = "INFO"

    captcha_api_key: str
    captcha_service: str

    delay_between_dependency_executions: list = '[10, 15]'

    @field_validator('console_log')
    def validate_console_log(cls, value):
        value.upper()
        valid_types = ["INFO", "DEBUG", "WARNING"]

        if value not in valid_types:
            raise ValueError(f"Invalid console log type message: '{value}'. Must be one of: {', '.join(valid_types)}")
        return value

    @field_validator('captcha_service')
    def validate_captcha_service(cls, value):
        valid_services = ["ANTI_CAPTCHA", "AZCAPTCHA", "CAPTCHA_GURU", "CPTCH_NET", "DEATHBYCAPTCHA", "RUCAPTCHA",
                          "TWOCAPTCHA", "MULTIBOT_CAPTCHA", "SCTG_CAPTCHA", "CAPMONSTER", "CAPSOLVER"]

        if value not in valid_services:
            raise ValueError(f"Invalid captcha service: '{value}'. Must be one of: {', '.join(valid_services)}")
        return value


    class Config:
        env_file = ".env"
        case_sensitive = False



class AppSettings(BaseSettings):
    captcha_website_url_waitlist: str = "https://www.zenchain.io"
    captcha_website_url_faucet: str = "https://faucet.zenchain.io"
    captcha_website_key_waitlist: str = "6Ld0snEqAAAAAN0MMJw_ZLHD6QEhjy94pojsgH9G"
    captcha_website_key_faucet: str = "6LdMHhUqAAAAADFN5eiFL2503Mn6HDJC6RRMh8NM"




class Settings(BaseSettings):
    env: EnvSettings = EnvSettings()
    app: AppSettings = AppSettings()


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
