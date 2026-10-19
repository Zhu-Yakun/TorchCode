@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\standalone-web.ps1" -Action Stop
if errorlevel 1 pause
