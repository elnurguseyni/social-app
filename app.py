from pathlib import Path
import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()


DATABASE = Path(__file__).with_name("social.db")


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get(
            "SECRET_KEY",
            "development-only-secret",
        ),
        DATABASE=os.environ.get("DATABASE", str(DATABASE)),
    )

    if test_config is not None:
        app.config.update(test_config)

    from social import register_routes
    register_routes(app)

    return app