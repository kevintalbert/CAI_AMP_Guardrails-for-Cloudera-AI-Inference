from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    config_dir: Path = Path(__file__).parent.parent / "config"
    frontend_dir: Path = Path(__file__).parent.parent / "frontend" / "out"
    host: str = "0.0.0.0"
    port: int = 8100

    @property
    def endpoints_file(self) -> Path:
        return self.config_dir / "endpoints.json"

    @property
    def guardrails_dir(self) -> Path:
        return self.config_dir / "guardrails"

    class Config:
        env_prefix = "GUARDRAILS_"
        env_file = ".env"


settings = Settings()
