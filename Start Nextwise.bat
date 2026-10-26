@echo off
setlocal
 title Nextwise
cd /d "%~dp0"
if not exist "nextwise - asset allocation\nextwise\app.py" goto missing_project
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 goto missing_python
if exist ".venv\Scripts\python.exe" goto install
 echo Preparing the Python environment...
python -m venv .venv
if errorlevel 1 goto failed
:install
 echo Installing or checking dependencies. The first launch can take a few minutes...
".venv\Scripts\python.exe" -m pip install -r "nextwise - asset allocation\nextwise\requirements.txt"
if errorlevel 1 goto failed
 echo Opening Nextwise. Keep this window open while using the dashboard.
".venv\Scripts\python.exe" -m streamlit run "nextwise - asset allocation\nextwise\app.py"
if errorlevel 1 goto failed
exit /b 0
:missing_project
 echo Extract the entire downloaded project ZIP before opening this launcher.
goto failed
:missing_python
 echo Python 3.10 or later is required. Install Python with the PATH option enabled.
goto failed
:failed
 echo.
 echo Nextwise could not start. The error is shown above.
pause
exit /b 1
