# ════════════════════════════════════════════════════════════════════════════
#  J.A.Y. Ollama Model Installer  —  Windows PowerShell
#  Usage:
#    .\scripts\install_models.ps1              # recommended set
#    .\scripts\install_models.ps1 -Mode all     # everything
#    .\scripts\install_models.ps1 -Mode minimal # tiny models only
#    .\scripts\install_models.ps1 -Mode check   # show what's installed
#    .\scripts\install_models.ps1 -Mode custom  # interactive picker
# ════════════════════════════════════════════════════════════════════════════

param(
    [ValidateSet("recommended","minimal","all","check","custom")]
    [string]$Mode = "recommended",
    [string]$OllamaUrl = "http://localhost:11434",
    [double]$RamBudgetGb = 7.0
)

$ErrorActionPreference = "Stop"

# ── Model catalogue ──────────────────────────────────────────────────────────
$Models = @(
    [PSCustomObject]@{ Id="llama3.2:3b";                                        RamGb=2.0; Speed="fast";   Purpose="Quick answers · voice replies";        Tier="minimal"     }
    [PSCustomObject]@{ Id="phi3:3.8b";                                          RamGb=2.3; Speed="fast";   Purpose="Fast reasoning · 128K context";        Tier="minimal"     }
    [PSCustomObject]@{ Id="mistral:7b-instruct-q4_K_M";                         RamGb=4.1; Speed="medium"; Purpose="General workhorse · trading";          Tier="recommended" }
    [PSCustomObject]@{ Id="llama3.1:8b-instruct-q4_K_M";                        RamGb=4.7; Speed="medium"; Purpose="Strong general AI · planning";         Tier="recommended" }
    [PSCustomObject]@{ Id="deepseek-coder-v2:16b-lite-instruct-q4_K_M";         RamGb=4.9; Speed="medium"; Purpose="Best local code model";                Tier="recommended" }
    [PSCustomObject]@{ Id="codellama:7b-instruct-q4_K_M";                       RamGb=3.8; Speed="medium"; Purpose="Code fallback (lighter)";              Tier="recommended" }
    [PSCustomObject]@{ Id="mixtral:8x7b-instruct-v0.1-q2_K";                   RamGb=6.5; Speed="slow";   Purpose="Powerful MoE · heavy analysis";        Tier="optional"    }
)

# ── Helpers ───────────────────────────────────────────────────────────────────

function Write-Header {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║     J.A.Y.  Ollama Model Installer               ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Test-OllamaRunning {
    try {
        $r = Invoke-WebRequest -Uri "$OllamaUrl/api/tags" -UseBasicParsing -TimeoutSec 4 -ErrorAction Stop
        return $r.StatusCode -eq 200
    } catch { return $false }
}

function Start-OllamaIfNeeded {
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
        Write-Host "✗ Ollama not found." -ForegroundColor Red
        Write-Host "  Download from: https://ollama.ai/download" -ForegroundColor Cyan
        exit 1
    }
    if (-not (Test-OllamaRunning)) {
        Write-Host "⚠  Ollama not running — starting it..." -ForegroundColor Yellow
        Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep 3
        if (-not (Test-OllamaRunning)) {
            Write-Host "✗ Could not start Ollama. Run 'ollama serve' manually." -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "✓ Ollama running at $OllamaUrl" -ForegroundColor Green
}

function Get-InstalledModels {
    try {
        $resp = Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -TimeoutSec 8
        return $resp.models | ForEach-Object { $_.name }
    } catch { return @() }
}

function Test-IsInstalled([string]$ModelId) {
    return (Get-InstalledModels) -contains $ModelId
}

function Test-FitsBudget([double]$ModelRam) {
    return $ModelRam -le $RamBudgetGb
}

function Invoke-Pull([PSCustomObject]$Model) {
    $id   = $Model.Id
    $ram  = $Model.RamGb
    $note = $Model.Purpose

    if (Test-IsInstalled $id) {
        Write-Host "  ✓ $id " -NoNewline -ForegroundColor Green
        Write-Host "(already installed)" -ForegroundColor DarkGray
        return
    }
    if (-not (Test-FitsBudget $ram)) {
        Write-Host "  ⚠  $id needs ${ram} GB but budget is ${RamBudgetGb} GB — skipped" -ForegroundColor Yellow
        return
    }

    Write-Host ""
    Write-Host "  ↓  Pulling $id  ($($ram) GB · $note)" -ForegroundColor Cyan
    try {
        & ollama pull $id
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓  $id installed" -ForegroundColor Green
        } else {
            Write-Host "  ✗  Pull failed for $id" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ✗  Error pulling $id`: $_" -ForegroundColor Red
    }
}

function Show-Catalogue {
    $installed = Get-InstalledModels
    Write-Host ""
    Write-Host ("  {0,-52} {1,-6} {2,-8} {3}" -f "Model ID", "RAM", "Speed", "Purpose") -ForegroundColor White
    Write-Host ("  {0,-52} {1,-6} {2,-8} {3}" -f ("-" * 52), "----", "--------", "-------") -ForegroundColor DarkGray
    foreach ($m in $Models) {
        $mark   = "  "
        $color  = "DarkGray"
        if ($installed -contains $m.Id)       { $mark = "✓ "; $color = "Green"  }
        if (-not (Test-FitsBudget $m.RamGb))  { $mark = "! "; $color = "Yellow" }
        $tierColor = switch ($m.Tier) {
            "minimal"     { "Green"   }
            "recommended" { "Cyan"    }
            "optional"    { "DarkGray"}
            default       { "White"   }
        }
        Write-Host ("  $mark{0,-50} {1,-6} {2,-8} " -f $m.Id, "$($m.RamGb)GB", $m.Speed) -NoNewline -ForegroundColor $color
        Write-Host $m.Purpose -ForegroundColor $tierColor
    }
    Write-Host ""
}

function Write-Summary {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║          Model installation complete             ║" -ForegroundColor Green
    Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "Installed models:" -ForegroundColor White
    $installed = Get-InstalledModels
    if ($installed.Count -eq 0) {
        Write-Host "  (none)" -ForegroundColor Yellow
    } else {
        $installed | ForEach-Object { Write-Host "  ✓  $_" -ForegroundColor Green }
    }
    Write-Host ""
    Write-Host "J.A.Y. will automatically choose the right model per task." -ForegroundColor DarkGray
    Write-Host "Start backend:  cd backend; uvicorn app.main:app --reload"   -ForegroundColor DarkGray
    Write-Host ""
}

# ── Mode handlers ─────────────────────────────────────────────────────────────

function Invoke-Minimal {
    Write-Host "`nInstalling minimal set (< 3 GB each):" -ForegroundColor Cyan
    $Models | Where-Object { $_.Tier -eq "minimal" } | ForEach-Object { Invoke-Pull $_ }
}

function Invoke-Recommended {
    Write-Host "`nInstalling recommended set:" -ForegroundColor Cyan
    Write-Host "  (models over ${RamBudgetGb} GB budget will be skipped)`n" -ForegroundColor DarkGray
    $Models | Where-Object { $_.Tier -in "minimal","recommended" } | ForEach-Object { Invoke-Pull $_ }
}

function Invoke-All {
    Write-Host "`nInstalling ALL models (this will take a while):" -ForegroundColor Yellow
    $Models | ForEach-Object { Invoke-Pull $_ }
}

function Invoke-Check {
    Show-Catalogue
}

function Invoke-Custom {
    Show-Catalogue
    Write-Host "Enter model IDs to install (space-separated), or press Enter to cancel:" -ForegroundColor White
    $input = Read-Host "> "
    if ([string]::IsNullOrWhiteSpace($input)) { Write-Host "Cancelled."; return }
    foreach ($modelId in $input.Trim().Split(" ")) {
        $found = $Models | Where-Object { $_.Id -eq $modelId }
        if ($found) {
            Invoke-Pull $found
        } else {
            Write-Host "  ⚠  '$modelId' not in catalogue — pulling anyway" -ForegroundColor Yellow
            & ollama pull $modelId
        }
    }
}

# ── Main ──────────────────────────────────────────────────────────────────────

Write-Header
Start-OllamaIfNeeded

switch ($Mode) {
    "check"       { Invoke-Check }
    "minimal"     { Invoke-Minimal;     Write-Summary }
    "recommended" { Invoke-Recommended; Write-Summary }
    "all"         { Invoke-All;         Write-Summary }
    "custom"      { Invoke-Custom;      Write-Summary }
}
