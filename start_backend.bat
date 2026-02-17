@echo off
echo Starting Nirbaan Backend Server...
cd /d "C:\Users\albit\OneDrive\Desktop\Nirbaan- A Therapy Management Project\backend"
call venv\Scripts\activate
echo Virtual environment activated
uvicorn app.main:app --reload --port 8000
