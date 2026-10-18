Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  Zero Trust Agroforestry & Sandalwood AI Platform - Frontend" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  Local Address:   http://localhost:3000" -ForegroundColor White
Write-Host "  Network Address: http://127.0.0.1:3000" -ForegroundColor White
Write-Host "  Backend Proxy:   http://127.0.0.1:8000" -ForegroundColor White
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

$frontendDir = Join-Path $PSScriptRoot "frontend"
Set-Location $frontendDir
npm run dev
