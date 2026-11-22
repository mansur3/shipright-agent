@echo off
rem Test copy of the frontend dev server: own build folder, talks to the throwaway backend from run_local.cmd.
rem The main frontend on :3000 and its backend on :8000 are left alone.
if not defined PORT set PORT=3001
if not defined API_ORIGIN set API_ORIGIN=http://localhost:8001
set NEXT_DIST_DIR=.next-qa
cd /d "%~dp0frontend"
npm run dev -- -p %PORT%
