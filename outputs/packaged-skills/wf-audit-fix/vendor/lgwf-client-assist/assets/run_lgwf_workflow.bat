@echo off
setlocal

set SCRIPT_DIR=%~dp0
set RUNNER=%SCRIPT_DIR%..\scripts\run_workflow.py

python "%RUNNER%" %*
