@echo off
setlocal

set "ROOT=%~dp0"

powershell -ExecutionPolicy Bypass -File "%ROOT%start-dev.ps1"

endlocal
