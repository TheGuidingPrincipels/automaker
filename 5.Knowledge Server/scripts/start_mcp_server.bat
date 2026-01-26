@echo off
REM MCP Knowledge Server Startup Script (Windows)
REM
REM This script starts the MCP Knowledge Management Server with proper
REM environment setup and error handling.
REM

setlocal EnableDelayedExpansion

echo =======================================================================
echo MCP Knowledge Server Startup
echo =======================================================================
echo.

REM Get script directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Check if virtual environment exists
if not exist ".venv" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv .venv
    echo Then: .venv\Scripts\activate
    echo Then: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist ".env" (
    echo [WARNING] .env file not found.
    if exist ".env.example" (
        echo Creating .env from .env.example...
        copy .env.example .env
        echo.
        echo [WARNING] Please edit .env with your Neo4j credentials before running again.
        pause
        exit /b 1
    ) else (
        echo [ERROR] .env.example not found!
        pause
        exit /b 1
    )
)

REM Check if Neo4j is running
echo Checking Neo4j connection...
docker ps | findstr neo4j >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Neo4j container not running!
    echo Attempting to start Neo4j...
    docker start neo4j >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Failed to start Neo4j. Please start it manually or run:
        echo    docker run -d --name neo4j -p 7474:7474 -p 7687:7687 ^
        echo        -e NEO4J_AUTH=neo4j/password neo4j:5-community
        pause
        exit /b 1
    )
    timeout /t 3 /nobreak >nul
)
echo [OK] Neo4j is running
echo.

REM Check if data directories exist
echo Checking data directories...
if not exist "data" mkdir data
if not exist "data\chroma" mkdir data\chroma
if not exist "data\embeddings" mkdir data\embeddings

REM Verify event store database exists
if not exist "data\events.db" (
    echo [WARNING] Event store database not found. Initializing...
    call .venv\Scripts\activate.bat
    python scripts\init_database.py
    if errorlevel 1 (
        echo [ERROR] Failed to initialize event store
        pause
        exit /b 1
    )
)
echo [OK] Data directories ready
echo.

REM Activate virtual environment
echo Activating Python virtual environment...
call .venv\Scripts\activate.bat

REM Verify Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo    Python version: %PYTHON_VERSION%

REM Verify key dependencies
echo Verifying dependencies...
python -c "import fastmcp, neo4j, chromadb, sentence_transformers" 2>nul
if errorlevel 1 (
    echo [ERROR] Missing dependencies!
    echo Please run: pip install -r requirements.txt
    pause
    exit /b 1
)
echo [OK] All dependencies installed
echo.

REM Start the server
echo =======================================================================
echo Starting MCP Knowledge Server...
echo    Server name: knowledge-server
echo    Press Ctrl+C to stop
echo =======================================================================
echo.

REM Run the server
python mcp_server.py

REM Cleanup on exit
echo.
echo =======================================================================
echo Server stopped
echo =======================================================================
pause
