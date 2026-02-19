from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/gemeenteraad"

    # LLM API keys
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Search (LinkedIn URL hydration)
    BRAVE_API_KEY: str = ""

    # Application
    ENVIRONMENT: str = "development"
    ELECTION_CONFIG: str = "data/elections/amsterdam-2026.yml"

    @property
    def election_config_path(self) -> Path:
        return Path(self.ELECTION_CONFIG)


settings = Settings()
