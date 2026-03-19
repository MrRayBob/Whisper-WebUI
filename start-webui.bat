@echo off

call venv\scripts\activate

if /I "%~1"=="--legacy" (
    shift
    echo Launching legacy Gradio UI...
    python app.py %*
    goto :eof
)

set HOST=0.0.0.0
set PORT=7860

:parse_args
if "%~1"=="" goto :run_fastapi

if /I "%~1"=="--host" (
    set HOST=%~2
    shift
    shift
    goto :parse_args
)
if /I "%~1"=="--server_name" (
    set HOST=%~2
    shift
    shift
    goto :parse_args
)
if /I "%~1"=="--port" (
    set PORT=%~2
    shift
    shift
    goto :parse_args
)
if /I "%~1"=="--server_port" (
    set PORT=%~2
    shift
    shift
    goto :parse_args
)

echo Unsupported flag for FastAPI mode: %~1
echo Use --legacy to launch the Gradio UI with legacy arguments.
exit /b 1

:run_fastapi
echo Launching FastAPI UI...
uvicorn backend.main:app --host %HOST% --port %PORT%

pause
