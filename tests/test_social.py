import pytest

from database import initialize_database
from social import app


@pytest.fixture
def client(tmp_path):
    app.config["TESTING"] = True
    app.config["DATABASE"] = str(tmp_path / "test.db")

    with app.app_context():
        initialize_database()

    with app.test_client() as client:
        yield client


def test_anonymous_user_cannot_post(client):
    response = client.post(
        "/posts",
        data={"content": "Should not be published"},
    )

    assert response.status_code == 302
    assert response.location.endswith("/login")

def test_user_can_register_and_post(client):
    response = client.post(
        "/register",
        data={
            "username": "casey",
            "email": "casey@example.com",
            "password": "secure-pass-123",
        },
    )

    assert response.status_code == 302
    assert response.location.endswith("/")

    response = client.post(
        "/posts",
        data={"content": "My first authenticated post"},
    )

    assert response.status_code == 302

    response = client.get("/")
    assert b"My first authenticated post" in response.data
    assert b"casey" in response.data