@echo off
title 쇼핑쇼츠 준비 상태 점검
cd /d "%~dp0"

node -v >nul 2>&1
if errorlevel 1 goto NONODE

node tools\check.js
echo.
pause
exit /b 0


:NONODE
echo.
echo   [없음] Node.js 가 실행되지 않습니다.
echo.
echo   설치.bat 을 먼저 실행하세요.
echo   직접 깔려면 https://nodejs.org 에서 LTS 버튼을 누르세요.
echo.
pause
exit /b 1
