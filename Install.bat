@echo off

if not exist "%~dp0\venv\Scripts" (
    echo Creating venv...
    python -m venv venv
)
echo checked the venv folder. now installing requirements..

call "%~dp0\venv\scripts\activate"

python -m pip install -U pip "setuptools<82" wheel || goto :fail
python -m pip install -r backend\requirements-backend.txt || goto :fail
python -m pip install --no-build-isolation -r requirements-legacy.txt || goto :fail

echo.
echo Requirements installed successfully.
goto :end

:fail
echo.
echo Requirements installation failed. please remove venv folder and run install.bat again.

:end
pause
