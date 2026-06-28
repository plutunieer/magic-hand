# =====================================================================
# PraxisHand — Vor-Ort-Installer (Windows)
# Richtet ALLES ein, was der PC braucht: die App + den lokalen
# Claude-Code-Agenten, der vor Ort einrichten/reparieren kann.
#
# Ausführen: Rechtsklick auf diese Datei -> "Mit PowerShell ausführen".
# (Falls blockiert:  PowerShell als Admin ->  Set-ExecutionPolicy -Scope
#  CurrentUser RemoteSigned  -> erneut versuchen.)
#
# Best-effort: bei Klinik-PCs ohne Adminrechte/winget bitte Python, Node
# und Claude Code manuell installieren lassen (siehe README).
# =====================================================================
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "== PraxisHand Setup ==" -ForegroundColor Cyan

function Have($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

# --- 1. Python ---
if (-not (Have python)) {
  Write-Host "Python wird installiert ..." -ForegroundColor Yellow
  winget install -e --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
}
Write-Host "Python: " (python --version)

# --- 2. virtuelle Umgebung + Abhängigkeiten ---
if (-not (Test-Path ".venv")) { python -m venv .venv }
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" -m playwright install chromium

# --- 3. Node.js (für Claude Code) ---
if (-not (Have node)) {
  Write-Host "Node.js wird installiert ..." -ForegroundColor Yellow
  winget install -e --id OpenJS.NodeJS.LTS --silent --accept-source-agreements --accept-package-agreements
  $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# --- 4. Claude Code (der Vor-Ort-Agent) ---
if (-not (Have claude)) {
  Write-Host "Claude Code wird installiert ..." -ForegroundColor Yellow
  npm install -g @anthropic-ai/claude-code
}

Write-Host ""
Write-Host "== Fertig ==" -ForegroundColor Green
Write-Host "Noch EINMAL nötig:" -ForegroundColor Cyan
Write-Host "  1. Anmeldung des KI-Helfers: 'Fix-mit-KI.bat' starten und den"
Write-Host "     Anweisungen folgen (Anthropic-Login / API-Key)."
Write-Host "  2. App starten: 'PraxisHand.exe' (oder  .\.venv\Scripts\python.exe -m praxishand.main)"
Write-Host "     Beim ersten Start öffnet sich der Einrichtungs-Assistent."
