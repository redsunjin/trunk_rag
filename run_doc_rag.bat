@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if exist "%PYTHON_EXE%" goto python_ready

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  set "PYTHON_EXE=python"
  goto python_ready
)

echo [doc_rag] Python runtime not found.
echo [doc_rag] Create .venv or install Python 3, then retry.
exit /b 1

:python_ready
echo [doc_rag] Python: %PYTHON_EXE%
start "doc_rag_server" cmd /k ""%PYTHON_EXE%" app_api.py"

echo [doc_rag] Waiting for server readiness...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$deadline=(Get-Date).AddSeconds(45); ^
$ok=$false; ^
while((Get-Date) -lt $deadline){ ^
  try { ^
    $res=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 2; ^
    if($res.StatusCode -eq 200){ $ok=$true; break } ^
  } catch {} ^
  Start-Sleep -Milliseconds 500 ^
}; ^
if($ok){ exit 0 } else { exit 1 }"

if %ERRORLEVEL%==0 (
  start "" "http://127.0.0.1:8000/intro"
  echo [doc_rag] Server is ready. Browser opened.
  echo [doc_rag] To stop server, close the 'doc_rag_server' terminal window or run stop_doc_rag.bat.
  exit /b 0
)

echo [doc_rag] Server launch requested, but /health was not ready within 45 seconds.
echo [doc_rag] Check the 'doc_rag_server' window for missing dependencies, port conflicts, or runtime errors.
exit /b 1
