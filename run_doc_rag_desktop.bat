@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "DESKTOP_DIR=%~dp0desktop\electron"

if not exist "%DESKTOP_DIR%\package.json" (
  echo [doc_rag desktop] desktop/electron package.json not found.
  exit /b 1
)

where npm >nul 2>nul
if not %ERRORLEVEL%==0 (
  echo [doc_rag desktop] npm not found.
  echo [doc_rag desktop] Install Node.js first, then retry.
  exit /b 1
)

if not exist "%DESKTOP_DIR%\node_modules\electron\package.json" (
  echo [doc_rag desktop] Electron dependencies not installed yet.
  echo [doc_rag desktop] Run: cd desktop\electron ^&^& npm install
  exit /b 1
)

pushd "%DESKTOP_DIR%"
echo [doc_rag desktop] Running preflight...
call npm run preflight
if not %ERRORLEVEL%==0 (
  echo [doc_rag desktop] Preflight failed. Resolve the reported runtime issues first.
  popd
  exit /b 1
)
popd

echo [doc_rag desktop] Launching Electron desktop launcher...
start "doc_rag_desktop" cmd /k "cd /d \"%DESKTOP_DIR%\" && npm start"
echo [doc_rag desktop] Desktop launcher started.
echo [doc_rag desktop] The Electron window will open /intro and manage the local server when needed.
exit /b 0
