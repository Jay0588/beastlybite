# J.A.Y. Startup Script (Windows PowerShell)

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   J.A.Y. — Just Assists You v0.1.0  ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pyVersion = python --version 2>&1
    Write-Host "✓ Python: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Install Python 3.10+ from python.org" -ForegroundColor Red
    exit 1
}

# Check .env
if (-not (Test-Path "backend\.env")) {
    Write-Host "⚠ Creating backend\.env from example..." -ForegroundColor Yellow
    Copy-Item "backend\.env.example" "backend\.env"
    Write-Host "  Edit backend\.env to configure API keys" -ForegroundColor Yellow
}

# Create venv if needed
if (-not (Test-Path "backend\.venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv backend\.venv
}

# Activate venv
& "backend\.venv\Scripts\Activate.ps1"

# Install deps
Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
pip install -r backend\requirements.txt -q --disable-pip-version-check

# Start backend
Write-Host "✓ Starting backend on http://localhost:8000" -ForegroundColor Green
$backend = Start-Process -FilePath "uvicorn" -ArgumentList "app.main:app --host 0.0.0.0 --port 8000 --reload" -WorkingDirectory "backend" -PassThru -WindowStyle Hidden

# Wait for backend
Write-Host "Waiting for backend..." -ForegroundColor Cyan
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing | Out-Null
        Write-Host "✓ Backend ready" -ForegroundColor Green
        $ready = $true
        break
    } catch {
        Start-Sleep 1
    }
}

# Install frontend deps
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
    Set-Location frontend
    npm install --silent
    Set-Location ..
}

# Start frontend
Write-Host "✓ Starting frontend on http://localhost:3000" -ForegroundColor Green
$frontend = Start-Process -FilePath "npm" -ArgumentList "run dev" -WorkingDirectory "frontend" -PassThru -WindowStyle Minimized

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║         J.A.Y. IS ONLINE             ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend:  http://localhost:3000" -ForegroundColor Cyan
Write-Host "  Backend:   http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API Docs:  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Open http://localhost:3000 in your browser" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow

# For Tauri desktop build:
# npm run tauri:build

try {
    Wait-Process -Id $backend.Id, $frontend.Id
} catch {
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
}
