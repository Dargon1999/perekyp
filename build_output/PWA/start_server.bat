@echo off
echo Starting MoneyTracker PWA Server...
echo.
echo After server starts, open browser and go to:
echo   http://localhost:5000
echo   or
echo   http://127.0.0.1:5000
echo.
echo To access from phone:
echo 1. Find your PC IP address (ipconfig)
echo 2. Open on phone: http://YOUR_IP:5000
echo.
python run_server.py
pause
