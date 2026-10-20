import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Keep the module-level app in app.main from touching the real dev database.
os.environ["ACEASSIST_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "import.db")

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def client(db_path):
    settings = Settings(db_path=db_path, frontend_origin="http://localhost:5173",
                        elevenlabs_api_key=None, elevenlabs_agent_id=None)
    return TestClient(create_app(settings))
