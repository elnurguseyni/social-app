import pytest

from app import create_app
from database import get_connection, initialize_database


@pytest.fixture
def client():
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": (
                "postgresql://social_user:local_password"
                "@localhost:5432/social_test"
            ),
        }
    )

    with app.app_context():
        initialize_database()

        connection = get_connection()
        connection.execute(
            """
            TRUNCATE TABLE
                likes,
                comments,
                posts,
                users
            RESTART IDENTITY CASCADE
            """
        )
        connection.commit()
        connection.close()

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

def test_user_can_like_and_comment(client):
    client.post(
        "/register",
        data={
            "username": "taylor",
            "email": "taylor@example.com",
            "password": "secure-pass-123",
        },
    )

    client.post(
        "/posts",
        data={"content": "A post to interact with"},
    )

    like_response = client.post("/posts/1/like")
    assert like_response.status_code == 302

    comment_response = client.post(
        "/posts/1/comments",
        data={"content": "Nice post!"},
    )
    assert comment_response.status_code == 302

    response = client.get("/")

    assert b"1 likes" in response.data
    assert b"Nice post!" in response.data
    assert b"taylor" in response.data