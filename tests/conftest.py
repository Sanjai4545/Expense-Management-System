import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# In-memory SQLite engine using StaticPool and check_same_thread=False
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@event.listens_for(test_engine, "connect")
def _fk_pragma(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_database():
    """Create fresh tables for every test."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def signup(client: TestClient, name: str, email: str, password: str = "Password123") -> dict:
    """Helper to signup and return auth headers."""
    resp = client.post("/api/auth/signup", json={"name": name, "email": email, "password": password})
    assert resp.status_code == 201, f"Signup failed: {resp.text}"
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def make_group(client: TestClient, headers: dict, name: str = "Test Group", members: list = None) -> dict:
    """Helper to create group and add members."""
    resp = client.post("/api/groups", json={"name": name}, headers=headers)
    assert resp.status_code == 201, f"Create group failed: {resp.text}"
    group_data = resp.json()
    group_id = group_data["id"]

    if members:
        for member_email in members:
            add_resp = client.post(
                f"/api/groups/{group_id}/members",
                json={"email": member_email},
                headers=headers,
            )
            assert add_resp.status_code == 201, f"Add member failed: {add_resp.text}"
        detail_resp = client.get(f"/api/groups/{group_id}", headers=headers)
        assert detail_resp.status_code == 200
        return detail_resp.json()

    return group_data
