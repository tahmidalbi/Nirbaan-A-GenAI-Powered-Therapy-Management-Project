@echo off
REM Setup script for Fear Ladder AI Education Feature

echo ================================
echo Fear Ladder Education Setup
echo ================================
echo.

echo Step 1: Installing frontend dependencies...
cd frontend
call npm install react-markdown
if %errorlevel% neq 0 (
    echo Error: Failed to install react-markdown
    pause
    exit /b 1
)
echo ✓ Frontend dependencies installed
echo.

echo Step 2: Creating database table...
cd ..\backend
python create_fear_ladder_education_table.py
if %errorlevel% neq 0 (
    echo Error: Failed to create database table
    pause
    exit /b 1
)
echo ✓ Database table created
echo.

echo ================================
echo ✓ Setup Complete!
echo ================================
echo.
echo Next steps:
echo 1. Make sure backend server is running (python -m uvicorn app.main:app --reload)
echo 2. Make sure frontend server is running (npm run dev)
echo 3. Navigate to Fear Ladder Education as a patient
echo 4. Click "Generate Education"
echo.
pause
