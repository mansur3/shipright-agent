"""
Database engine and session management.
Uses SQLite with WAL mode for safe concurrent reads.

Users are never seeded with passwords written in source. Seed from the environment:
  SANKALP_ADMIN_PASSWORD   creates the admin account (12+ characters)
  SANKALP_DEMO_USERS=1     also creates the five role accounts for a demo, all with SANKALP_DEMO_PASSWORD (12+ characters)
Without either variable the app starts with no users and logs how to create one.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine, text

log = logging.getLogger(__name__)

# Serverless hosts give a read-only code folder; /tmp is writable but not persistent. The database only holds derived results and users.
_DEFAULT_DB = Path("/tmp/sankalp.db") if os.getenv("VERCEL") else Path(__file__).resolve().parent / "sankalp.db"
DB_PATH = Path(os.getenv("SANKALP_DB_PATH", str(_DEFAULT_DB)))
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

# Columns added after the first release; an existing database is upgraded in place.
_NEW_BATCH_COLUMNS = {
    "t1_claims": "INTEGER DEFAULT 0", "t1_inr": "REAL DEFAULT 0", "t2_claims": "INTEGER DEFAULT 0", "t2_inr": "REAL DEFAULT 0",
    "t3_claims": "INTEGER DEFAULT 0", "t3_inr": "REAL DEFAULT 0", "t4_claims": "INTEGER DEFAULT 0", "t4_inr": "REAL DEFAULT 0",
    "pending_t12_claims": "INTEGER DEFAULT 0",
}


def init_db() -> None:
    """Create all tables, upgrade older ones, enable WAL mode and seed users from the environment."""
    SQLModel.metadata.create_all(engine)
    _migrate()
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()
    _seed_default_users()
    ensure_public_demo_users()


def _migrate() -> None:
    with engine.connect() as conn:
        have = {r[1] for r in conn.execute(text("PRAGMA table_info(batch_runs)")).fetchall()}
        for col, ddl in _NEW_BATCH_COLUMNS.items():
            if col not in have:
                conn.execute(text(f"ALTER TABLE batch_runs ADD COLUMN {col} {ddl}"))
        conn.commit()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def _seed_default_users() -> None:
    """Create accounts from environment variables if the users table is empty. No password is ever stored in source."""
    from db.models import User, RoleEnum
    from auth.security import hash_password
    from sqlmodel import select

    admin_pw = os.getenv("SANKALP_ADMIN_PASSWORD", "")
    demo_on = os.getenv("SANKALP_DEMO_USERS", "") == "1"
    demo_pw = os.getenv("SANKALP_DEMO_PASSWORD", "")
    accounts: list[tuple[dict, str]] = []
    if len(admin_pw) >= 12:
        accounts.append(({"username": "admin", "email": "admin@pfizer.internal", "role": RoleEnum.admin}, admin_pw))
    if demo_on and len(demo_pw) >= 12:
        accounts += [
            ({"username": "cfo", "email": "cfo@pfizer.internal", "role": RoleEnum.cfo}, demo_pw),
            ({"username": "supply", "email": "supply@pfizer.internal", "role": RoleEnum.supply_chain}, demo_pw),
            ({"username": "claims", "email": "claims@pfizer.internal", "role": RoleEnum.claims_finance}, demo_pw),
            ({"username": "rsm_north", "email": "rsm_n@pfizer.internal", "role": RoleEnum.sales_rsm, "cnf": "CF-N01"}, demo_pw),
            ({"username": "cnf_east", "email": "cnf_e@pfizer.internal", "role": RoleEnum.cnf_agent, "cnf": "CF-E01"}, demo_pw),
        ]
        if not admin_pw:
            accounts.append(({"username": "admin", "email": "admin@pfizer.internal", "role": RoleEnum.admin}, demo_pw))
    with Session(engine) as session:
        if session.exec(select(User)).first():
            return
        if not accounts:
            log.warning("No users created. Set SANKALP_ADMIN_PASSWORD (12+ chars), or SANKALP_DEMO_USERS=1 with SANKALP_DEMO_PASSWORD, then restart.")
            return
        for u, pw in accounts:
            session.add(User(username=u["username"], email=u["email"], role=u["role"], hashed_password=hash_password(pw), cnf_code=u.get("cnf")))
        session.commit()


DEMO_ROLES = {"claims_finance": "demo_claims", "supply_chain": "demo_supply", "cfo": "demo_cfo"}


def public_demo_enabled() -> bool:
    return os.getenv("SANKALP_PUBLIC_DEMO", "") == "1"


def ensure_public_demo_users() -> None:
    """When SANKALP_PUBLIC_DEMO=1 the panel can enter as a read role without a password. These accounts get random passwords nobody knows,
    are never admin, and are reachable only through /api/auth/demo-login."""
    if not public_demo_enabled():
        return
    import secrets
    from db.models import User, RoleEnum
    from auth.security import hash_password
    from sqlmodel import select
    with Session(engine) as session:
        for role, name in DEMO_ROLES.items():
            if session.exec(select(User).where(User.username == name)).first():
                continue
            session.add(User(username=name, email=f"{name}@demo.invalid", role=RoleEnum(role), hashed_password=hash_password(secrets.token_urlsafe(24))))
        session.commit()
