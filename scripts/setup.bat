@echo off
REM PhantomLink Core - Setup and Run Script

echo ====================================
echo PhantomLink Core - Setup
echo ====================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
echo.

echo ====================================
echo Setup complete!
echo ====================================
echo.
echo To start the server, run:
echo   venv\Scripts\activate
echo   python main.py
echo.
echo To test the stream, run:
echo   python test_client.py sample
echo   python test_client.py 10
echo.

pause
