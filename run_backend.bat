@echo off
title Zero Trust Agroforestry - Backend Console
echo =================================================================
echo   Zero Trust Agroforestry ^& Sandalwood AI Platform - Backend
echo =================================================================
echo   API:     http://127.0.0.1:8000
echo   Docs:    http://127.0.0.1:8000/docs
echo   Health:  http://127.0.0.1:8000/health
echo =================================================================
echo.
cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
) else (
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
)
pause
