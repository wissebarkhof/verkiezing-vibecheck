from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Election


TEST_SLUG = "amsterdam-2026"


def _mock_election() -> Election:
    """Return a minimal Election object suitable for route tests."""
    e = MagicMock(spec=Election)
    e.id = 1
    e.slug = TEST_SLUG
    e.name = "Gemeenteraadsverkiezingen Amsterdam 2026"
    e.city = "amsterdam"
    e.date = date(2026, 3, 18)
    return e


def _mock_db():
    """Return a MagicMock DB session where queries return sensible empty values."""
    db = MagicMock()
    election = _mock_election()

    # db.query(Election).filter(...).first() → election
    # db.query(X).first() → None for non-election models
    def query_side_effect(model):
        mock_q = MagicMock()
        if model is Election:
            mock_q.filter.return_value.first.return_value = election
            mock_q.order_by.return_value.all.return_value = [election]
            mock_q.all.return_value = [election]
            mock_q.first.return_value = election
        else:
            mock_q.filter.return_value.first.return_value = None
            mock_q.filter.return_value.all.return_value = []
            mock_q.first.return_value = None
            mock_q.all.return_value = []

        # Support arbitrary chain depth for non-terminal steps
        for attr in ("join", "options", "order_by", "with_entities", "offset", "limit"):
            getattr(mock_q, attr).return_value = mock_q
            getattr(mock_q.filter.return_value, attr).return_value = mock_q.filter.return_value

        mock_q.filter.return_value.count.return_value = 0
        mock_q.count.return_value = 0

        return mock_q

    db.query.side_effect = query_side_effect
    db.execute.return_value.fetchall.return_value = []
    return db


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: _mock_db()
    yield TestClient(app)
    app.dependency_overrides.clear()
