@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD=python"
python --version >nul 2>nul
if errorlevel 1 set "PYTHON_CMD=py -3"
call %PYTHON_CMD% --version >nul 2>nul
if errorlevel 1 goto :no_python

if not exist ".buildenv\Scripts\python.exe" (
  echo Creating build environment...
  call %PYTHON_CMD% -m venv .buildenv
  if errorlevel 1 goto :error
)

echo Installing build packages...
".buildenv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements-build.txt
if errorlevel 1 goto :error

echo Building single-file EXE...
".buildenv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name AIImagePublisherLite --icon "assets\app.ico" --add-data "assets;assets" app.py
if errorlevel 1 goto :error

echo.
echo Build complete: dist\AIImagePublisherLite.exe
pause
exit /b 0

:no_python
echo Python was not found. Install Python 3.10 or newer.
pause
exit /b 1

:error
echo.
echo Build failed. Review the error above.
pause
exit /b 1

