@echo off
setlocal

cd /d "%~dp0"
echo [doc_rag] Trying to stop local server...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$root=(Resolve-Path '.').Path; ^
$procs=Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'app_api\.py' -and $_.CommandLine -like ('*'+$root+'*') }; ^
if($procs -and $procs.Count -gt 0){ ^
  $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('[doc_rag] Stopped PID ' + $_.ProcessId) }; ^
  exit 0 ^
} else { ^
  Write-Host '[doc_rag] No matching app_api.py process found in this project.'; ^
  exit 1 ^
}"

if %ERRORLEVEL%==0 (
  echo [doc_rag] Stop complete.
) else (
  echo [doc_rag] Nothing to stop.
)
