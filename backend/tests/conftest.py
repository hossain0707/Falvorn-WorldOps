import os
from pathlib import Path
import tempfile
import pytest

# Set environment before app import; global engine/settings are created on import.
_tmp = tempfile.TemporaryDirectory(prefix='worldops_tests_')
os.environ['APP_ENV'] = 'development'
os.environ['DATABASE_URL'] = f"sqlite:///{Path(_tmp.name) / 'test.sqlite'}"
os.environ.pop('API_KEY', None)
os.environ.pop('LLM_API_KEY', None)

from fastapi.testclient import TestClient  # noqa: E402
from app.core.database import Base, engine  # noqa: E402
from app.domain import models  # noqa: E402, F401
from app.main import app  # noqa: E402

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def world(client):
    r = client.post('/api/v1/worlds',json={'name':'Research Testbed','seed':13})
    assert r.status_code == 201, r.text
    return r.json()
