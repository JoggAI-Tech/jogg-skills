@echo off
setlocal
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0smart-video.ps1" %*
exit /b %ERRORLEVEL%
