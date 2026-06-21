@echo off
REM Instagram Automation Tracker - Scheduled Run
REM Use this with Windows Task Scheduler

set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

REM Log file with timestamp
set LOG_FILE=logs\tracker_%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%.log
set LOG_FILE=%LOG_FILE: =0%

if not exist logs mkdir logs

echo [%DATE% %TIME%] Starting Instagram tracker... >> "%LOG_FILE%"
python main.py track -i 0 >> "%LOG_FILE%" 2>&1
echo [%DATE% %TIME%] Finished. >> "%LOG_FILE%"
