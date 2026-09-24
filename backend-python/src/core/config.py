from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "KinoStats API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Matches docker-compose coordinates from Java backend
    POSTGRES_USER: str = "cinema"
    POSTGRES_PASSWORD: str = "secretpassword"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "kinostats"

    TMDB_API_KEY: str = ""
    TMDB_API_URL: str = "https://api.themoviedb.org/3"

    @property
    def async_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()