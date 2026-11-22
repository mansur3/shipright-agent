"""Vercel entry point for the API. The app lives in backend/ and imports its own packages (agent, auth, routers),
so put backend/ on the path first. Every API route starts with /api, which vercel.json sends here."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import app  # noqa: E402,F401  (Vercel looks for the name `app`)
