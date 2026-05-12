$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = Join-Path $backend "venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
  throw "Backend virtual environment Python was not found at $python"
}

Write-Host "Starting FastAPI on http://127.0.0.1:8000 ..."
$backendJob = Start-Job -Name "pgagi-backend" -ScriptBlock {
  param($backendPath, $pythonPath)
  Set-Location $backendPath
  & $pythonPath -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} -ArgumentList $backend, $python

$ready = $false
for ($i = 0; $i -lt 30; $i++) {
  Start-Sleep -Seconds 1
  if ($backendJob.State -ne "Running") {
    Receive-Job $backendJob
    throw "FastAPI stopped before it became reachable."
  }

  try {
    Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -UseBasicParsing -TimeoutSec 1 | Out-Null
    $ready = $true
    break
  } catch {
    Write-Host "Waiting for FastAPI..."
  }
}

if (-not $ready) {
  Stop-Job $backendJob -ErrorAction SilentlyContinue
  Receive-Job $backendJob -ErrorAction SilentlyContinue
  throw "FastAPI did not become reachable on http://127.0.0.1:8000."
}

Write-Host "FastAPI is ready."
Write-Host "Starting Next.js. Keep this window open. Press Ctrl+C to stop the frontend."

try {
  Set-Location $frontend
  npm run dev
} finally {
  Write-Host "Stopping FastAPI..."
  Stop-Job $backendJob -ErrorAction SilentlyContinue
  Receive-Job $backendJob -ErrorAction SilentlyContinue
  Remove-Job $backendJob -Force -ErrorAction SilentlyContinue
}
