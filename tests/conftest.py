import os

os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5433/url_shortener_test",
)

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import engine
from app.main import app


@pytest.fixture(scope="session")
def apply_migrations():
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(scope="session")
def client(apply_migrations):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_database(client):
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE urls RESTART IDENTITY"))
    yield
