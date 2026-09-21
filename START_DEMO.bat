@echo off
rem Starts CleanProof on this laptop (backend + frontend). The public link runs in the cloud
rem (Vercel) and does not need this laptop. Close the two windows it opens to stop everything.
cd /d "%~dp0"
rem Make sure Node.js is found even if Windows has not refreshed PATH since it was installed
set "PATH=C:\Program Files\nodejs;%PATH%"

choice /c YN /n /t 10 /d N /m "Reset demo data? This DELETES all complaints reported so far. Y = reset, N = keep (auto N in 10s): "
if errorlevel 2 goto keepdata
backend\venv\Scripts\python.exe scripts\reset_demo.py
if errorlevel 1 (
  echo Reset failed. Is another backend window still open? Close it and try again.
  pause
  exit /b 1
)
:keepdata

start "CleanProof backend" cmd /k "cd /d "%~dp0backend" && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
start "CleanProof frontend" cmd /k "cd /d "%~dp0frontend" && "C:\Program Files\nodejs\npm.cmd" run dev"

echo Waiting for the servers to start...
timeout /t 8 /nobreak > nul

start "" msedge "https://localhost:5173/dashboard"

echo.
echo CleanProof is starting:
echo   - Laptop:  https://localhost:5173  (opened in Edge)
echo   - Public:  https://cleanproof-seven.vercel.app  (cloud, works without this laptop)
echo.
pause
