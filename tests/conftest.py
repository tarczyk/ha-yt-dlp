import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    state_file = tmp_path / "update-state.json"
    application = create_app(state_path=str(state_file))
    application.config["TESTING"] = True
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def ha_supervisor_token(monkeypatch):
    """Set SUPERVISOR_TOKEN for tests that require HA notification (Story 2.2)."""
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-supervisor-token")
    yield "test-supervisor-token"


@pytest.fixture
def no_supervisor_token(monkeypatch):
    """Ensure SUPERVISOR_TOKEN is absent — simulates Docker/non-HA mode."""
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    yield
