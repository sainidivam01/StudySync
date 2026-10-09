import pytest
from app import create_app
import db


@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "DB_BACKEND": "sqlite",
                      "SQLITE_PATH": str(tmp_path / "test.db"), "SECRET_KEY": "test"})
    with app.app_context():
        db.init_db()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(client):
    """A registered, signed-in user (pseudonym test account)."""
    client.post("/register", data={"email": "t1@example.com", "password": "password123"})
    return client


def first_subject(c):
    return c.get("/api/subjects").get_json()[0]["subject_id"]


def log(c, when, minutes=60, sid=None):
    return c.post("/api/sessions", json={"subject_id": sid or first_subject(c),
                                          "start_time": when, "minutes": minutes})
