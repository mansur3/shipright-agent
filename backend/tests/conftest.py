"""
Test configuration — session-scoped DB setup.

Strategy:
- Use a dedicated test DB at db/test_sankalp.db (deleted before/after session)
- Patch db.database.engine BEFORE any app module imports it
- tool tests (test_tools.py, test_rules.py) use real CSV data, no DB needed
- API tests (test_api.py) use the TestClient which triggers lifespan → init_db
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

# ── Point to a throw-away test DB ─────────────────────────────────────────────
_STARTER = Path(__file__).resolve().parent.parent
TEST_DB   = _STARTER / "db" / "test_sankalp.db"


def _use_test_db() -> None:
    """
    Swap the production engine for a test-specific one.
    Must be called before any module that imports db.database.engine.
    """
    import db.database as dbd
    from sqlmodel import create_engine, text, SQLModel

    TEST_DB.unlink(missing_ok=True)
    test_url = f"sqlite:///{TEST_DB}"
    new_engine = create_engine(
        test_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    dbd.engine       = new_engine
    dbd.DATABASE_URL = test_url

    # Import all models so their tables register on SQLModel.metadata
    import db.models  # noqa: F401

    # Create all tables on the new engine
    SQLModel.metadata.create_all(new_engine)
    with new_engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()

    # Seed test users from the environment, exactly as production does. No password lives in source.
    from auth import ratelimit
    ratelimit.ENABLED = False
    os.environ["SANKALP_DEMO_USERS"] = "1"
    os.environ["SANKALP_DEMO_PASSWORD"] = "Test-Passw0rd-2026"
    os.environ["SANKALP_ADMIN_PASSWORD"] = "Test-Passw0rd-2026"
    dbd._seed_default_users()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initialise test DB and run batch once for the whole session."""
    _use_test_db()

    from db.database import engine
    from batch.processor import run_batch
    from sqlmodel import Session

    with Session(engine) as session:
        run_batch(session)

    yield

    try:
        TEST_DB.unlink(missing_ok=True)
    except PermissionError:
        pass  # Windows file lock — OK, will be overwritten on next run
