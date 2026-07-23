param(
    [int]$Port = 5000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $project

if (-not (Test-Path '.venv')) {
    Write-Host '[local] Creating virtual environment...' -ForegroundColor Cyan
    python -m venv .venv
}

Write-Host '[local] Installing dependencies...' -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

$env:PORT = "$Port"
Write-Host "[local] Starting app on http://localhost:$Port" -ForegroundColor Green
.\.venv\Scripts\python.exe app.py
