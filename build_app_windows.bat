@echo off
REM ── interiorcad Stammdaten Tool – Windows App Builder ────────────────────────
setlocal

set SCRIPT_DIR=%~dp0
set PY_SCRIPT=%SCRIPT_DIR%main.py
set ICON=%SCRIPT_DIR%AppIcon.ico
set APP_NAME=interiorcad Stammdaten

echo Pruefe Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python nicht gefunden. Bitte von https://python.org installieren.
    pause
    exit /b 1
)
echo Python gefunden.

echo.
echo Installiere pyinstaller...
python -m pip install pyinstaller --quiet
echo pyinstaller installiert.

echo.
echo Baue App...
cd /d "%SCRIPT_DIR%"
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

if exist "%ICON%" (
    python -m PyInstaller --windowed --onefile --name "%APP_NAME%" --icon "%ICON%" "%PY_SCRIPT%"
) else (
    python -m PyInstaller --windowed --onefile --name "%APP_NAME%" "%PY_SCRIPT%"
)

echo.
if exist "dist\%APP_NAME%.exe" (
    echo App erfolgreich gebaut!
    echo Speicherort: %SCRIPT_DIR%dist\%APP_NAME%.exe
    explorer dist
) else (
    echo Build fehlgeschlagen.
    pause
    exit /b 1
)
pause
