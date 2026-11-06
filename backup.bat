@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "PYTHON=%PROJECT_DIR%.venv\Scripts\python.exe"
set "BACKUP_DIR=%PROJECT_DIR%backups"
set "LOG_FILE=%BACKUP_DIR%\backup.log"

rem Optional: a second place to copy the backups to, for example E:\SDLG-backups
rem Leave it empty to skip.
set "EXTRA_DIR="

set "RESULT=0"

if not exist "%PYTHON%" (
    echo Virtual environment Python was not found: "%PYTHON%"
    set "RESULT=1"
    goto :done
)

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
if errorlevel 1 (
    set "RESULT=1"
    goto :done
)

>>"%LOG_FILE%" echo [%date% %time%] Starting backup.
"%PYTHON%" "%PROJECT_DIR%manage.py" backup_db >>"%LOG_FILE%" 2>&1
if errorlevel 1 set "RESULT=1"

if exist "%PROJECT_DIR%media" (
    robocopy "%PROJECT_DIR%media" "%BACKUP_DIR%\media" /E /NFL /NDL /NJH /NJS /NP >>"%LOG_FILE%" 2>&1
    if errorlevel 8 set "RESULT=1"
)

if defined EXTRA_DIR (
    robocopy "%BACKUP_DIR%" "%EXTRA_DIR%" /E /NFL /NDL /NJH /NJS /NP >>"%LOG_FILE%" 2>&1
    if errorlevel 8 set "RESULT=1"
)

if "%RESULT%"=="0" (
    >>"%LOG_FILE%" echo [%date% %time%] Backup completed successfully.
    echo Backup completed successfully.
) else (
    >>"%LOG_FILE%" echo [%date% %time%] Backup finished with errors.
    echo Backup finished with errors. See "%LOG_FILE%" for details.
)

:done
if /i not "%~1"=="nopause" pause
exit /b %RESULT%