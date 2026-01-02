@echo off
REM Financial Email Agent - Quick Start Script
REM This script activates the virtual environment and runs the agent

echo ============================================================
echo Financial Email Agent - Starting
echo ============================================================
echo.

cd /d %~dp0
call venv\Scripts\activate

echo Running health check...
python health_check.py
if errorlevel 1 (
    echo.
    echo [ERROR] Health check failed. Please fix issues before running.
    pause
    exit /b 1
)

echo.
echo Health check passed! Starting agent...
echo.
python src/main.py

echo.
echo ============================================================
echo Agent execution completed
echo ============================================================
pause

@REM Made with Bob
