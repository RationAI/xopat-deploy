$ErrorActionPreference = "Stop"

Write-Host "=== Build WSI-Service (Windows) ==="

$RepoRoot   = Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\..")
$WsiDir     = Join-Path $RepoRoot "external\wsi-service"
$WsiDistDir = Join-Path $WsiDir "dist\wsi_service_binary"
$RootDist   = Join-Path $RepoRoot "dist"

$EnvTemplate = Join-Path $RepoRoot "envs\wsi_service.env"
$EnvFile     = Join-Path $WsiDir ".env"

$RunSrc = Join-Path $RepoRoot "scripts\run\run_wsi_service_win.py"
$SpecSrc = Join-Path $RepoRoot "scripts\specs\wsi_service_win.spec"
$RunDst = Join-Path $WsiDir "run_wsi_service.py"
$SpecDst = Join-Path $WsiDir "wsi_service.spec"

$LibsWinDir = Join-Path $RepoRoot "libs\windows"

if (-not (Test-Path $WsiDir))  { throw "Missing submodule: $WsiDir" }
if (-not (Test-Path $RunSrc))  { throw "Missing: $RunSrc" }
if (-not (Test-Path $SpecSrc)) { throw "Missing: $SpecSrc" }

& py -3.12 --version | Out-Null

if (Test-Path $EnvTemplate) { Copy-Item $EnvTemplate $EnvFile -Force }

Set-Location $WsiDir

# Windows: remove uvloop from pyproject.toml
$PyProject = Join-Path $WsiDir "pyproject.toml"
if (Test-Path $PyProject) {
  $content = Get-Content $PyProject -Raw
  if ($content -match "uvloop") {
    $filtered = ($content -split "`n") | Where-Object { $_ -notmatch "uvloop" }
    Set-Content -Path $PyProject -Value ($filtered -join "`n") -NoNewline
  }
}

if (Test-Path ".\venv") { Remove-Item -Recurse -Force ".\venv" }

& py -3.12 -m venv venv
& ".\venv\Scripts\Activate.ps1"

python -m pip install -U pip wheel setuptools pyinstaller
pip install poetry

poetry lock
poetry install

python -c "import uvicorn, fastapi; print('deps OK')"
try { python -c "import imagecodecs" | Out-Null } catch { pip install imagecodecs }

Copy-Item $RunSrc  $RunDst  -Force
Copy-Item $SpecSrc $SpecDst -Force

if (-not (Test-Path $LibsWinDir)) { Write-Host "WARNING: missing $LibsWinDir (OpenSlide DLLs)" }

pyinstaller --clean wsi_service.spec

if (-not (Test-Path $WsiDistDir)) { throw "Build failed: $WsiDistDir not found" }

New-Item -ItemType Directory -Force -Path $RootDist | Out-Null
Copy-Item $WsiDistDir $RootDist -Recurse -Force

Write-Host "OK: $(Join-Path $RootDist 'wsi_service_binary\wsi_service_binary.exe')"