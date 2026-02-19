"""Smoke tests — verify every route returns a successful HTTP response.

These tests use a mocked DB session so no real database is required.
"""


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Verkiezing Vibecheck" in response.text


def test_parties_list(client):
    response = client.get("/partijen/")
    assert response.status_code == 200


def test_party_detail_not_found(client):
    response = client.get("/partijen/9999")
    assert response.status_code == 200  # template renders "not found" gracefully


def test_candidates_list(client):
    response = client.get("/kandidaten/")
    assert response.status_code == 200


def test_candidate_detail_not_found(client):
    response = client.get("/kandidaten/9999")
    assert response.status_code == 200  # template renders "not found" gracefully


def test_compare(client):
    response = client.get("/vergelijk/")
    assert response.status_code == 200


def test_search_empty_query(client):
    response = client.get("/zoeken/")
    assert response.status_code == 200


def test_404(client):
    response = client.get("/bestaat-niet")
    assert response.status_code == 404
    assert "404" in response.text
