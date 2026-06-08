@echo off
title Jarvis Mark 1
cd /d "%~dp0"
echo.
echo  ========================================
echo     J.A.R.V.I.S. Mark 1
echo     Just A Rather Very Intelligent System
echo  ========================================
echo.

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.11+.
    pause
    exit /b 1
)

:: Run Jarvis
python run.py
if errorlevel 1 (
    echo.
    echo [ERROR] Jarvis failed to start.
    pause
)
