@echo off
title Zero Trust Agroforestry - Frontend Console
echo =================================================================
echo   Zero Trust Agroforestry ^& Sandalwood AI Platform - Frontend
echo =================================================================
echo   Local Address:   http://localhost:3000
echo   Network Address: http://127.0.0.1:3000
echo   Backend Proxy:   http://127.0.0.1:8000
echo =================================================================
echo.
cd /d "%~dp0frontend"
npm run dev
pause
