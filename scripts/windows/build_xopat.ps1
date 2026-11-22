$ErrorActionPreference = "Stop"
Write-Host "=== Build xOpat (Windows) ==="

$RootDir           = Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\..")
$XopatDir          = Join-Path $RootDir "external\xopat"
$RootDist          = Join-Path $RootDir "dist"
$OutputBin         = Join-Path $XopatDir "xopat_binary.exe"

if (-not (Test-Path $XopatDir))          { throw "Missing submodule: $XopatDir" }

Set-Location $XopatDir
# npm ci, not npm install: every server bundle records a content hash of
# node_modules/.package-lock.json in its build key, so an install that silently
# moves a transitive dependency makes two releases from one commit differ.
npm ci
Copy-Item "$XopatDir\env\env.default.json" "$XopatDir\env\env.json" -Force
# Builds the client bundles AND prebuilds every plugin/module *.server.* entry
# (grunt serverBuild). The binary carries no compiler, so an entry missing here
# answers RPC_UNKNOWN_METHOD for the life of the release.
npm run build
# @yao-pkg/pkg: the maintained fork (vercel/pkg is archived and caps out at
# node18). Pinned by the xOpat lockfile rather than a global install.
npx @yao-pkg/pkg . --targets node22-win-x64 --output $OutputBin

if (-not (Test-Path $OutputBin)) { throw "Build failed: $OutputBin not found" }

New-Item -ItemType Directory -Force -Path (Join-Path $RootDist "xopat") | Out-Null
Copy-Item $OutputBin (Join-Path $RootDist "xopat\xopat_binary.exe") -Force

Write-Host "OK: $RootDist\xopat\xopat_binary.exe"