@echo off
echo === Nirbaan ERP Model Setup ===
echo.

where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Ollama is not installed.
    echo Download and install it from: https://ollama.com/download
    echo Then re-run this script.
    pause
    exit /b 1
)

echo Ollama found.
echo Registering nirbaan-erp-federated model...
echo This will download ~4.5GB on first run. Please wait.
echo.

ollama create nirbaan-erp-federated -f "%~dp0Modelfile"

if %errorlevel% equ 0 (
    echo.
    echo SUCCESS! Model registered as: nirbaan-erp-federated
    echo You can now start the Nirbaan backend.
) else (
    echo.
    echo FAILED. Make sure Ollama is running: open a terminal and run "ollama serve"
    echo Then re-run this script.
)
pause
