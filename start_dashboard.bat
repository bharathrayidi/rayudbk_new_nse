@echo off
:: NSE Dashboard Startup Script
:: Starts both the FastAPI backend and Vite frontend

echo ============================================
echo  NSE Market Intelligence Dashboard Launcher
echo ============================================
echo.

set NSE_ROOT=d:\badri\vs code\google_work\nse
set NSE_FRONT=d:\badri\vs code\google_work\nse\frontend

echo.
:: Start FastAPI backend
echo [1/2] Starting FastAPI backend on http://localhost:8000 ...
start "NSE Backend (FastAPI)" cmd /k pushd "%NSE_ROOT%" ^& python -m uvicorn backend.server:app --host 0.0.0.0 --port 8000 --reload

:: Wait 3 seconds for backend to boot
timeout /t 3 /nobreak

:: Start Vite frontend
echo [2/2] Starting Vite frontend on http://localhost:5180 ...
start "NSE Frontend (Vite)" cmd /k pushd "%NSE_FRONT%" ^& npm run dev

echo.
echo ============================================
echo  Servers are starting in new windows!
echo  Backend:  http://localhost:8000/docs
echo  Frontend: http://localhost:5180
echo ============================================
echo.
timeout /t 5 /nobreak

