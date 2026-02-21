@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if exist "%PYTHON_EXE%" goto run

set "PYTHON_EXE=C:\Users\sunji\llm_5th\001_chatbot\.venv\Scripts\python.exe"
if exist "%PYTHON_EXE%" goto run

set "PYTHON_EXE=python"

:run
echo [doc_rag] Python: %PYTHON_EXE%
start "doc_rag_server" cmd /k ""%PYTHON_EXE%" app_api.py"
timeout /t 2 > nul
start "" "http://127.0.0.1:8000/intro"

echo [doc_rag] Server launch requested. Browser opened.
echo [doc_rag] To stop server, close the 'doc_rag_server' terminal window.
