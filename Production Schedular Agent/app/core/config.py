from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GOOGLE_API_KEY: str
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str = "scheduler-docs"

    class Config:
        env_file = ".env"

settings = Settings()
