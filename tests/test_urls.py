import pytest

from app.db import SessionLocal
from app.main import generate_short_code
from app.models import URL

EXAMPLE_URL = "https://example.com/some/page"


def create_short_url(client, url=EXAMPLE_URL):
    response = client.post("/shorten", json={"url": url})
    assert response.status_code == 201
    return response.json()


def test_health_returns_healthy(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_shorten_creates_short_url(client):
    data = create_short_url(client)

    assert data["original_url"] == EXAMPLE_URL
    assert len(data["short_code"]) == 6
    assert data["short_url"].endswith("/" + data["short_code"])
    assert data["click_count"] == 0


def test_redirect_goes_to_original_url(client):
    data = create_short_url(client)

    response = client.get(f"/{data['short_code']}", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == EXAMPLE_URL


def test_redirect_increments_click_count(client):
    data = create_short_url(client)

    client.get(f"/{data['short_code']}", follow_redirects=False)
    client.get(f"/{data['short_code']}", follow_redirects=False)

    with SessionLocal() as db:
        url = db.query(URL).filter(URL.short_code == data["short_code"]).one()

    assert url.click_count == 2


def test_unknown_short_code_returns_404(client):
    response = client.get("/doesnotexist", follow_redirects=False)

    assert response.status_code == 404


@pytest.mark.parametrize(
    "bad_url",
    ["not-a-url", "ftp://example.com/file", "javascript:alert(1)"],
)
def test_invalid_url_is_rejected(client, bad_url):
    response = client.post("/shorten", json={"url": bad_url})

    assert response.status_code == 422


def test_generate_short_code_uses_letters_and_digits():
    code = generate_short_code(10)

    assert len(code) == 10
    assert code.isalnum()