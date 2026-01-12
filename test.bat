@echo off
REM Test runner batch file for Windows

echo ====================================
echo PhantomLink Test Suite
echo ====================================
echo.

REM Activate virtual environment
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    echo Virtual environment activated
) else (
    echo WARNING: Virtual environment not found
    echo Run setup.bat first
    pause
    exit /b 1
)

REM Check if pytest is installed
python -c "import pytest" 2>nul
if errorlevel 1 (
    echo Installing test dependencies...
    pip install pytest pytest-asyncio pytest-cov
)

echo.
echo Running tests...
echo.

REM Temporarily rename __init__.py to avoid import conflicts
if exist __init__.py (
    ren __init__.py __init__.py.tmp
    set RENAMED=1
) else (
    set RENAMED=0
)

REM Run tests based on argument
if "%1"=="unit" (
    echo Running unit tests only...
    pytest test_models.py test_data_loader.py test_playback_engine.py test_session_manager.py -v
) else if "%1"=="integration" (
    echo Running integration tests only...
    pytest test_server.py -v
) else if "%1"=="coverage" (
    echo Running tests with coverage...
    pytest --cov=. --cov-report=html --cov-report=term-missing
    echo.
    echo Coverage report generated in htmlcov\index.html
) else if "%1"=="fast" (
    echo Running fast tests only...
    pytest -m "not slow" -v
) else (
    echo Running all tests...
    pytest -v
)

REM Restore __init__.py if it was renamed
if %RENAMED%==1 (
    ren __init__.py.tmp __init__.py
)

echo.
echo ====================================
echo Test run complete
echo ====================================
pause
