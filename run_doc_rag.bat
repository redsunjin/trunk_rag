@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "BOOTSTRAP_PYTHON=%~dp0.venv\Scripts\python.exe"
if exist "%BOOTSTRAP_PYTHON%" goto bootstrap_ready

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  set "BOOTSTRAP_PYTHON=python"
  goto bootstrap_ready
)

echo [doc_rag] Python runtime not found.
echo [doc_rag] Create .venv, install requirements.txt, or install Python 3, then retry.
exit /b 1

:bootstrap_ready
echo [doc_rag] Bootstrapping single web MVP path...
"%BOOTSTRAP_PYTHON%" scripts\bootstrap_web_release.py --bootstrap-python "%BOOTSTRAP_PYTHON%"
if not %ERRORLEVEL%==0 (
  echo [doc_rag] Bootstrap failed.
  echo [doc_rag] Check Python installation, network access for requirements install, and local runtime prerequisites.
  exit /b 1
)

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
  echo [doc_rag] Expected .venv\Scripts\python.exe after bootstrap, but it was not found.
  exit /b 1
)

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
echo [doc_rag] First-run bootstrap already prepared .venv, .env, and runtime dependencies when possible.
echo [doc_rag] If the LLM or embedding model is missing, follow README.md release web MVP guide.
exit /b 1
