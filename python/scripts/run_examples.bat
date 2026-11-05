@echo off
set "PYTHONPATH=%~dp0..\src;%PYTHONPATH%"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0..\..\examples\python\run_all.py" %*
) else (
    python "%~dp0..\..\examples\python\run_all.py" %*
)
set rc=%errorlevel%
pause
exit /b %rc%
