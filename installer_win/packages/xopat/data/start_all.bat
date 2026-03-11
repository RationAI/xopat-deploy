@echo off
set "BASEDIR=%~dp0"
echo Starting WSI-Service...
pushd "%BASEDIR%wsi-service"
start "" /b "wsi_service_binary.exe"
popd
timeout /t 3 >nul
echo Starting xOpat...
set "XOPAT_ENV=%BASEDIR%xopat\env\env.default.json"
start "" /b "%BASEDIR%xopat\xopat_binary.exe"
timeout /t 2 >nul
start "" "http://localhost:9000/"