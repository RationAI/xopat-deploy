$ErrorActionPreference = "Stop"
Write-Host "=== Build xOpat (Windows) ==="

$RootDir           = Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\..")
$XopatDir          = Join-Path $RootDir "external\xopat"
$RootDist          = Join-Path $RootDir "dist"
$OutputBin         = Join-Path $XopatDir "xopat_binary.exe"

if (-not (Test-Path $XopatDir))          { throw "Missing submodule: $XopatDir" }

Set-Location $XopatDir
npm install
npm run build
npx pkg . --targets node18-win-x64 --output $OutputBin

if (-not (Test-Path $OutputBin)) { throw "Build failed: $OutputBin not found" }

New-Item -ItemType Directory -Force -Path (Join-Path $RootDist "xopat") | Out-Null
Copy-Item $OutputBin (Join-Path $RootDist "xopat\xopat_binary.exe") -Force

Write-Host "OK: $RootDist\xopat\xopat_binary.exe"