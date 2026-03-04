$ErrorActionPreference = "Stop"
Write-Host "=== Build xOpat (Windows) ==="

$RootDir           = Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\..")
$XopatDir          = Join-Path $RootDir "external\xopat"
$RootDist          = Join-Path $RootDir "dist"
$OutputBin         = Join-Path $XopatDir "xopat_binary.exe"
# TODO: remove once package.json is updated in xopat
$CustomJsonPackage = Join-Path $RootDir "scripts\linux\xopat_package.json"
$JsonPackage       = Join-Path $XopatDir "package.json"
# TODO: remove once env is handled differently
$EnvSrc            = Join-Path $RootDir "envs\xopat_env.json"
$EnvTarget         = Join-Path $XopatDir "env\env.json"

if (-not (Test-Path $XopatDir))          { throw "Missing submodule: $XopatDir" }
if (-not (Test-Path $CustomJsonPackage)) { throw "Missing: $CustomJsonPackage" }
if (-not (Test-Path $EnvSrc))            { throw "Missing: $EnvSrc" }

# TODO: remove once package.json is updated in xopat
Copy-Item $CustomJsonPackage $JsonPackage -Force

# TODO: remove once env is handled differently
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $EnvTarget) | Out-Null
Copy-Item $EnvSrc $EnvTarget -Force


Set-Location $XopatDir
npm install
npm run build
npx pkg . --targets node18-win-x64 --output $OutputBin

if (-not (Test-Path $OutputBin)) { throw "Build failed: $OutputBin not found" }

New-Item -ItemType Directory -Force -Path (Join-Path $RootDist "xopat") | Out-Null
Copy-Item $OutputBin (Join-Path $RootDist "xopat\xopat_binary.exe") -Force

Write-Host "OK: $RootDist\xopat\xopat_binary.exe"