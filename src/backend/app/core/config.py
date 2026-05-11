from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "WikiBFS API"
    WIKIDATA_ENDPOINT: str = "https://query.wikidata.org/sparql"
    USER_AGENT: str = "WikiBFS/1.0 (https://github.com/LeeVHoangtk3/name-related-searching; contact: leviethoangtk3@gmail.com)"
    TIMEOUT: int = 20
    DEFAULT_LIMIT: int = 50
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"

settings = Settings()
