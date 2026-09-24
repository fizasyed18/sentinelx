import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-not-a-real-key")
os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test_sentinelx.db"
os.environ["API_KEY"] = "test-key"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.agents import graph as graph_module
from tests.fakes import fake_call_llm_json


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch):
    """Patch the one function every agent node calls, so the full test
    suite (including the API/integration tests) runs deterministically
    and offline. The real ChatOpenAI path in app/agents/llm.py is used
    as-is outside of tests."""
    monkeypatch.setattr(graph_module, "call_llm_json", fake_call_llm_json)


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine("sqlite:///./test_sentinelx.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("./test_sentinelx.db")
    except OSError:
        pass


@pytest.fixture()
def db_session(test_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(test_engine, db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
