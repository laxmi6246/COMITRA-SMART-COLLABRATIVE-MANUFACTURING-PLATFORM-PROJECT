@echo off
title CoMitra - Smart Collaborative Manufacturing Platform
color 0B
echo =======================================================================
echo          CoMitra - Smart Collaborative Manufacturing Platform
echo          "One Order. Multiple Manufacturers. One Success."
echo =======================================================================
echo.

:: Navigate to script directory
cd /d "%~dp0"
if exist "comitra_flask" cd comitra_flask

:: Find Python Executable
set PYTHON_EXE=python
if exist "C:\Users\LAXMI PRASANNA\AppData\Local\Programs\Python\Python313\python.exe" (
    set "PYTHON_EXE=C:\Users\LAXMI PRASANNA\AppData\Local\Programs\Python\Python313\python.exe"
)

echo [1/3] Using Python: %PYTHON_EXE%

:: Check database
if not exist "comitra.db" (
    echo [2/3] Initializing and seeding live demonstration database...
    "%PYTHON_EXE%" seed.py
) else (
    echo [2/3] Live demonstration database ready: comitra.db
)

echo [3/3] Starting CoMitra Live Server on http://localhost:5000 ...
echo.
echo =======================================================================
echo   Server is running! 
echo   Opening browser automatically in 2 seconds...
echo   Keep this black window OPEN while demonstrating to faculty.
echo =======================================================================
echo.

:: Automatically open browser after 2 seconds
start "" timeout /t 2 /nobreak >nul & start http://localhost:5000

:: Start the Flask app
"%PYTHON_EXE%" app.py

pause
