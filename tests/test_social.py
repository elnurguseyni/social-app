import pytest
import re
from app import create_app
from database import (
    get_connection,
    initialize_database,
    create_user,
    add_post,
    add_comment,
    like_post,
    delete_post,
)
def post_with_csrf(client, path, data=None):
    page = client.get("/login")
    assert page.status_code == 200

    match = re.search(
        r'name="csrf_token"\s+value="([^"]+)"',
        page.get_data(as_text=True),
    )
    assert match is not None, "Login form is missing its CSRF token"

    form_data = dict(data or {})
    form_data["csrf_token"] = match.group(1)

    return client.post(path, data=form_data)

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

@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_delete_rejects_missing_or_invalid_csrf(client, token):
    with client.application.app_context():
        owner_id = create_user(
            "owner", "owner@example.com", "secure-pass-123"
        )
        post_id = add_post("Keep this post", owner_id)

    with client.session_transaction() as session:
        session["user_id"] = owner_id

    # Establish a real CSRF token in this client's session.
    client.get("/login")

    data = {}
    if token is not None:
        data["csrf_token"] = token

    # Deliberately bypass post_with_csrf to submit a bad request.
    response = client.post(f"/posts/{post_id}/delete", data=data)

    assert response.status_code == 400
    assert b"CSRF" in response.data

    with client.application.app_context():
        with get_connection() as connection:
            post = connection.execute(
                "SELECT id FROM posts WHERE id = %s",
                (post_id,),
            ).fetchone()

    assert post is not None

def test_anonymous_user_cannot_post(client):
    response = post_with_csrf(client,
        "/posts",
        data={"content": "Should not be published"},
    )

    assert response.status_code == 302
    assert response.location.endswith("/login")

def test_user_can_register_and_post(client):
    response = post_with_csrf(client,
        "/register",
        data={
            "username": "casey",
            "email": "casey@example.com",
            "password": "secure-pass-123",
        },
    )

    assert response.status_code == 302
    assert response.location.endswith("/")

    response = post_with_csrf(client,
        "/posts",
        data={"content": "My first authenticated post"},
    )

    assert response.status_code == 302

    response = client.get("/")
    assert b"My first authenticated post" in response.data
    assert b"casey" in response.data

def test_user_can_like_and_comment(client):
    post_with_csrf(client,
        "/register",
        data={
            "username": "taylor",
            "email": "taylor@example.com",
            "password": "secure-pass-123",
        },
    )

    post_with_csrf(client,
        "/posts",
        data={"content": "A post to interact with"},
    )

    like_response = post_with_csrf(client,"/posts/1/like")
    assert like_response.status_code == 302

    comment_response = post_with_csrf(client,
        "/posts/1/comments",
        data={"content": "Nice post!"},
    )
    assert comment_response.status_code == 302

    response = client.get("/")

    assert b"1 likes" in response.data
    assert b"Nice post!" in response.data
    assert b"taylor" in response.data

def test_user_profile_shows_user_posts(client):
    post_with_csrf(client,
        "/register",
        data={
            "username": "profileuser",
            "email": "profile@example.com",
            "password": "secure-pass-123",
        },
    )

    post_with_csrf(client,
        "/posts",
        data={"content": "A profile post"},
    )

    response = client.get("/users/profileuser")

    assert response.status_code == 200
    assert b"profileuser" in response.data
    assert b"A profile post" in response.data

def test_missing_profile_returns_404(client):
    response = client.get("/users/unknown-user")

    assert response.status_code == 404

def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.data == b"ok"

def test_readiness_check(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.data == b"ready"


@pytest.mark.parametrize(
    "username,email",
    [
        ("casey", "different@example.com"),
        ("different", "casey@example.com"),
    ],
)
def test_duplicate_registration_shows_error(client, username, email):
    post_with_csrf(client,
        "/register",
        data={
            "username": "casey",
            "email": "casey@example.com",
            "password": "secure-pass-123",
        },
    )
    post_with_csrf(client, "/logout")

    response = post_with_csrf(client,
        "/register",
        data={
            "username": username,
            "email": email,
            "password": "another-pass-123",
        },
    )

    assert response.status_code == 200
    assert b"That account already exists." in response.data

@pytest.mark.parametrize("is_owner", [True, False])
def test_post_deletion_checks_ownership(client, is_owner):
    with client.application.app_context():
        owner_id = create_user(
            "owner", "owner@example.com", "secure-pass-123"
        )
        other_id = create_user(
            "other", "other@example.com", "secure-pass-456"
        )
        post_id = add_post("A post to delete", owner_id)

        like_post(other_id, post_id)
        add_comment("A comment", other_id, post_id)

        requesting_user = owner_id if is_owner else other_id
        result = delete_post(post_id, requesting_user)

        assert result is is_owner

        with get_connection() as connection:
            counts = connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM posts
                    WHERE id = %s) AS posts,
                    (SELECT COUNT(*) FROM likes
                    WHERE post_id = %s) AS likes,
                    (SELECT COUNT(*) FROM comments
                    WHERE post_id = %s) AS comments
                """,
                (post_id, post_id, post_id),
            ).fetchone()

        expected = 0 if is_owner else 1
        assert counts == {
            "posts": expected,
            "likes": expected,
            "comments": expected,
        }
@pytest.mark.parametrize("visitor", ["owner", "other", "anonymous"])
def test_delete_route_checks_session_identity(client, visitor):
    with client.application.app_context():
        owner_id = create_user(
            "owner", "owner@example.com", "secure-pass-123"
        )
        other_id = create_user(
            "other", "other@example.com", "secure-pass-456"
        )
        post_id = add_post("Protected post", owner_id)

    if visitor != "anonymous":
        with client.session_transaction() as session:
            session["user_id"] = (
                owner_id if visitor == "owner" else other_id
            )

    response = post_with_csrf(client,
        f"/posts/{post_id}/delete",
        data={"user_id": owner_id},
    )

    if visitor == "owner":
        assert response.status_code == 302
        assert response.location.endswith("/")
    elif visitor == "other":
        assert response.status_code == 404
    else:
        assert response.status_code == 302
        assert response.location.endswith("/login")

    with client.application.app_context():
        with get_connection() as connection:
            post = connection.execute(
                "SELECT id FROM posts WHERE id = %s",
                (post_id,),
            ).fetchone()

    assert (post is None) == (visitor == "owner")