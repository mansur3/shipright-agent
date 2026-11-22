"""Build the static frontend and place it in backend/public, which the API serves (and Vercel serves as static files).
Run from ShipRight_Agent:  python build_frontend.py
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD_DIR = ".next-build"
FRONT, PUBLIC = ROOT / "frontend", ROOT / "backend" / "public"

shutil.rmtree(FRONT / BUILD_DIR, ignore_errors=True)  # a stale export would otherwise ship removed pages
env = dict(os.environ, NEXT_EXPORT="1", NEXT_DIST_DIR=BUILD_DIR)  # own build folder: a running `next dev` keeps its .next
npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
subprocess.run([npm, "run", "build"], cwd=FRONT, env=env, check=True)
if PUBLIC.exists():
    shutil.rmtree(PUBLIC)
shutil.copytree(FRONT / BUILD_DIR, PUBLIC)  # with NEXT_DIST_DIR set, the export lands in that folder, not out/
print("copied", FRONT / BUILD_DIR, "->", PUBLIC)
