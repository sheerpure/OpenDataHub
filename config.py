from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://postgres:Azxs1226@localhost:5432/opendatahub"

    class Config:
        env_file = ".env"  # 未來可以用 .env 檔藏密碼

settings = Settings()