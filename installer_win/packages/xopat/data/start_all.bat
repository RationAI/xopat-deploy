@echo off
set "BASEDIR=%~dp0"
echo Starting WSI-Service...
start "" /b "%BASEDIR%wsi-service\wsi_service_binary.exe"
timeout /t 3 >nul
echo Starting xOpat...
start "" /b "%BASEDIR%xopat\xopat_binary.exe"
timeout /t 2 >nul
start "" "http://localhost:9000/"