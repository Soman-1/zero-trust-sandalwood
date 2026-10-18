Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  Zero Trust Agroforestry & Sandalwood AI Platform - Backend" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  API:     http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  Docs:    http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  Health:  http://127.0.0.1:8000/health" -ForegroundColor White
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = "python"
}

& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
