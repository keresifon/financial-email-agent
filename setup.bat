@echo off
REM Financial Email Agent - Setup Script (Windows)
REM This script automates the setup process for the Financial Email Agent

echo ==========================================
echo Financial Email Agent - Setup
echo ==========================================
echo.

REM Check Python version
echo Checking Python version...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% found
echo.

echo Step 1: Creating virtual environment...
if exist venv (
    echo [INFO] Virtual environment already exists. Skipping creation.
) else (
    python -m venv venv
    echo [OK] Virtual environment created
)
echo.

echo Step 2: Activating virtual environment...
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated
echo.

echo Step 3: Upgrading pip...
python -m pip install --upgrade pip setuptools wheel
echo [OK] pip upgraded
echo.

echo Step 4: Installing dependencies...
pip install -r requirements.txt
echo [OK] Core dependencies installed
echo.

if exist requirements-dev.txt (
    set /p INSTALL_DEV="Install development dependencies? (y/n): "
    if /i "%INSTALL_DEV%"=="y" (
        pip install -r requirements-dev.txt
        echo [OK] Development dependencies installed
    )
)
echo.

echo Step 5: Creating necessary directories...
if not exist logs mkdir logs
if not exist credentials mkdir credentials
if not exist data\attachments mkdir data\attachments
if not exist data\processed mkdir data\processed
echo [OK] Directories created
echo.

echo Step 6: Setting up configuration...
if not exist .env (
    copy .env.example .env
    echo [OK] .env file created from template
    echo [INFO] Please edit .env file with your configuration
) else (
    echo [INFO] .env file already exists
)

if not exist config\config.yaml (
    copy config\config.example.yaml config\config.yaml
    echo [OK] config.yaml created from template
    echo [INFO] Please edit config\config.yaml with your settings
) else (
    echo [INFO] config.yaml already exists
)
echo.

echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo [INFO] Next steps:
echo 1. Configure Gmail API:
echo    - Visit https://console.cloud.google.com/
echo    - Create a new project
echo    - Enable Gmail API
echo    - Create OAuth 2.0 credentials
echo    - Download credentials.json to project root
echo.
echo 2. Set up MongoDB:
echo    - Install MongoDB locally OR use MongoDB Atlas
echo    - Update MONGODB_CONNECTION_STRING in .env
echo.
echo 3. Install Ollama:
echo    - Visit https://ollama.ai/
echo    - Download and install Ollama
echo    - Run: ollama pull llama3.1:8b
echo.
echo 4. Update configuration:
echo    - Edit .env file with your settings
echo    - Edit config\config.yaml if needed
echo.
echo 5. Test the setup:
echo    - Run: python src\main.py
echo.
echo [OK] Happy coding! 🚀
echo.
pause

@REM Made with Bob
