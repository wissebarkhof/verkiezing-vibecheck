from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


def _mock_db():
    """Return a MagicMock DB session where queries return empty results."""
    db = MagicMock()
    # Terminal query methods return sensible empty values
    db.query.return_value.first.return_value = None
    db.query.return_value.all.return_value = []
    # Support arbitrary method chains (.filter, .join, .options, .order_by, etc.)
    # MagicMock auto-creates chained attributes; override the terminal calls.
    for chain in [
        db.query.return_value.filter.return_value,
        db.query.return_value.join.return_value.filter.return_value,
        db.query.return_value.filter.return_value.order_by.return_value,
        db.query.return_value.join.return_value.filter.return_value.options.return_value.order_by.return_value,
        db.query.return_value.join.return_value.filter.return_value.filter.return_value.order_by.return_value,
    ]:
        chain.first.return_value = None
        chain.all.return_value = []
    return db


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: _mock_db()
    yield TestClient(app)
    app.dependency_overrides.clear()
