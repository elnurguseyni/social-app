from pathlib import Path

from flask import Flask


DATABASE = Path(__file__).with_name("social.db")


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_mapping(
        SECRET_KEY="development-secret-change-later",
        DATABASE=DATABASE,
    )

    if test_config is not None:
        app.config.update(test_config)

    from social import register_routes
    register_routes(app)

    return app