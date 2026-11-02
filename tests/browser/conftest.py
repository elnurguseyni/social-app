from threading import Thread

import pytest
from werkzeug.serving import make_server

from app import create_app
from database import initialize_database, get_connection, create_user, add_post


@pytest.fixture
def live_server():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "browser-tests-only",
            "DATABASE_URL": (
                "postgresql://social_user:local_password"
                "@localhost:5432/social_browser_test"
            ),
        }
    )

    with app.app_context():
        initialize_database()

        with get_connection() as connection:
            assert connection.info.dbname == "social_browser_test"

            connection.execute(
                "TRUNCATE TABLE likes, comments, posts, users RESTART IDENTITY"
            )

        user_id = create_user(
            "browser_user",
            "browser@example.com",
            "browser-test-password",
        )
        add_post("A post for browser testing", user_id)
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()