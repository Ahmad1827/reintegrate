@echo off
rem Reintegrate launcher for Windows. First run sets up a private Python environment.
setlocal
pushd "%~dp0"
set "VENV=%LOCALAPPDATA%\Reintegrate\venv"
if not exist "%VENV%\Scripts\python.exe" (
  echo First run: setting things up, this takes a few minutes...
  py -3.11 -m venv "%VENV%" 2>nul || py -3.12 -m venv "%VENV%" 2>nul || py -3.10 -m venv "%VENV%" 2>nul || python -m venv "%VENV%"
  if not exist "%VENV%\Scripts\python.exe" (
    echo Could not find Python. Install Python 3.11 from python.org and run this again.
    pause
    popd
    exit /b 1
  )
  "%VENV%\Scripts\python.exe" -m pip install --quiet --upgrade pip
  "%VENV%\Scripts\python.exe" -m pip install --quiet -r requirements.txt
  echo Installing hand tracking for the camera...
  "%VENV%\Scripts\python.exe" -m pip install --quiet -r requirements-camera.txt || echo Hand tracking could not be installed - the game will run with keyboard only.
)
"%VENV%\Scripts\python.exe" main.py %*
if errorlevel 1 pause
popd
