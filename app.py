from pathlib import Path
import os
from flask import Flask
from dotenv import load_dotenv
import logging
import sys
from flask_wtf.csrf import CSRFProtect

load_dotenv()

csrf = CSRFProtect()


DATABASE = Path(__file__).with_name("social.db")

def configure_logging(app):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    )

    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

def create_app(test_config=None):
    app = Flask(__name__)
    configure_logging(app)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get(
            "SECRET_KEY",
            "development-only-secret",
        ),
        DATABASE_URL=os.environ.get(
            "DATABASE_URL",
            "postgresql://social_user:local_password@localhost:5432/social_db",
        ),
    )

    if test_config is not None:
        app.config.update(test_config)

    csrf.init_app(app)

    from social import register_routes
    register_routes(app)
    return app