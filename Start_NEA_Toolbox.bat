@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  set PYTHON=py -3.12
) else (
  set PYTHON=python
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating the NEA Toolbox environment...
  %PYTHON% -m venv .venv
  if errorlevel 1 goto :python_error
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :install_error
python -m pip install -r requirements.txt
if errorlevel 1 goto :install_error

python app.py
goto :eof

:python_error
echo.
echo Python 3.12 could not be started.
echo Ask school IT to install Python 3.12 with Tk support, or use the packaged Windows build.
pause
exit /b 1

:install_error
echo.
echo NEA Toolbox dependencies could not be installed.
echo Check internet access or ask school IT for help.
pause
exit /b 1
