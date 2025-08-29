@echo off
setlocal ENABLEEXTENSIONS

REM Ir al directorio donde está este .bat
cd /d "%~dp0"

REM Preferir un virtualenv local si existe (.venv o venv)
if exist ".venv\Scripts\pythonw.exe" (
  ".venv\Scripts\pythonw.exe" "%~dp0personal_boss.py"
  goto :eof
)
if exist "venv\Scripts\pythonw.exe" (
  "venv\Scripts\pythonw.exe" "%~dp0personal_boss.py"
  goto :eof
)

REM Intentar el lanzador sin consola (pyw)
where pyw >nul 2>nul
if %errorlevel%==0 (
  pyw "%~dp0personal_boss.py"
  goto :eof
)

REM Fallback con consola (si lo llamás desde el .vbs se oculta igual)
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0personal_boss.py"
  goto :eof
)

REM Últimos recursos
where pythonw >nul 2>nul
if %errorlevel%==0 (
  pythonw "%~dp0personal_boss.py"
  goto :eof
)

python "%~dp0personal_boss.py"
