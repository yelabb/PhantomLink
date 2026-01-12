@echo off
REM Quick start script for PhantomLink Core

echo Starting PhantomLink Core server...
echo.

call ..\\.venv\Scripts\activate.bat
cd ..
python main.py
