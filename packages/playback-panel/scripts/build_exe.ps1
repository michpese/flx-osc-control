# Baut die eigenständige Windows-Datei dist\flx-panel.exe mit einem Befehl.
# Aufruf aus dem Repo-Wurzelverzeichnis oder direkt per Rechtsklick -> Mit PowerShell ausführen.

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location $RepoRoot

Write-Host "==> Baue flx-panel.exe im Ordner dist\ ..." -ForegroundColor Cyan
uv run --package playback-panel --extra build flx-panel-build @args

Write-Host ""
Write-Host "Fertig! Die ausführbare Datei liegt unter:" -ForegroundColor Green
Write-Host "  $(Join-Path $RepoRoot 'dist\flx-panel.exe')"
