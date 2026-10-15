@echo off
REM ============================================================
REM   task-system -> GitHub  one-click pusher
REM   Pure ASCII intentionally: cmd parses this file as GBK
REM   before chcp 65001 applies, so any UTF-8 CJK here would
REM   mojibake. All Chinese output lives in push-to-github.ps1
REM   which ships with a UTF-8 BOM.
REM
REM   Usage:
REM     push-to-github.bat              auto-detect channel
REM     push-to-github.bat -Mode https  force HTTPS
REM     push-to-github.bat -Mode ssh    force SSH over 443
REM ============================================================

chcp 65001 >nul 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -NoExit -File "%~dp0push-to-github.ps1" %*

if errorlevel 1 (
  echo.
  echo   Push did not succeed. See messages above.
  pause
)
