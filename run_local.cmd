@echo off
rem Local run of the single app (API + static frontend) on http://127.0.0.1:8000. Uses a throwaway database in %TEMP%.
if not defined SANKALP_ADMIN_PASSWORD set SANKALP_ADMIN_PASSWORD=local-%RANDOM%%RANDOM%%RANDOM%-admin
if not defined SECRET_KEY set SECRET_KEY=%RANDOM%%RANDOM%%RANDOM%%RANDOM%%RANDOM%%RANDOM%%RANDOM%%RANDOM%
set SANKALP_PUBLIC_DEMO=1
set SANKALP_DB_PATH=%TEMP%\sankalp_local.db
if exist "%SANKALP_DB_PATH%" del "%SANKALP_DB_PATH%"
if not defined PORT set PORT=8000
cd /d "%~dp0backend"
.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port %PORT%
