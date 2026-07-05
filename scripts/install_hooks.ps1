$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$repoPath = $repoRoot.Path
git -c "safe.directory=$repoPath" -C $repoPath config core.hooksPath .githooks

Write-Host "Installed Seekphony Git hooks from .githooks"
