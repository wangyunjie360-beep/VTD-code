@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"
set "PY314_EXE=C:\Python314\python.exe"

pushd "%REPO_ROOT%" >NUL
set "PYTHONPATH=%REPO_ROOT%\src;%PYTHONPATH%"

where py >NUL 2>NUL
if not errorlevel 1 (
    py -3.14 -m openscenario_mcp
) else if exist "%PY314_EXE%" (
    "%PY314_EXE%" -m openscenario_mcp
) else (
    echo Could not locate Python 3.14 via the py launcher or "%PY314_EXE%".
    set "EXIT_CODE=9009"
    popd >NUL
    exit /b %EXIT_CODE%
)

set "EXIT_CODE=%ERRORLEVEL%"
popd >NUL

exit /b %EXIT_CODE%
