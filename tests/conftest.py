from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

with patch.dict(
    "os.environ",
    {
        "DATABASE_URL": "sqlite://",
        "SECRET_KEY": "local-test-signing-key",
        "ALGORITHM": "HS256",
    },
):
    from app.databased import Base, get_db
    from app.main import app
    from app.models.leave_type import LeaveType


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(LeaveType(id=2, name="Casual Leave"))
            db.commit()
            yield db
    finally:
        engine.dispose()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
