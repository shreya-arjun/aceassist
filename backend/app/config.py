import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR.parent / ".env")


@dataclass(frozen=True)
class Settings:
    db_path: str
    frontend_origin: str
    elevenlabs_api_key: str | None
    elevenlabs_agent_id: str | None
    agent_tools_secret: str | None = None

    @property
    def voice_configured(self) -> bool:
        return bool(self.elevenlabs_api_key and self.elevenlabs_agent_id)


def load_settings() -> Settings:
    return Settings(
        db_path=os.getenv("ACEASSIST_DB_PATH", str(BACKEND_DIR / "aceassist.db")),
        frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
        elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY") or None,
        elevenlabs_agent_id=os.getenv("ELEVENLABS_AGENT_ID") or None,
        agent_tools_secret=os.getenv("AGENT_TOOLS_SECRET") or None,
    )
