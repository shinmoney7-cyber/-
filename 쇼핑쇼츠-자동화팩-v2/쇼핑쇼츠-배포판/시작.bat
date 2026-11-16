@echo off
title 쇼핑쇼츠 만들기
cd /d "%~dp0"

call claude --version >nul 2>&1
if errorlevel 1 goto NOCLAUDE

cls
echo.
echo   ============================================
echo     쇼핑쇼츠 만들기
echo   ============================================
echo.
echo   아래 문장을 복사해서 클로드에게 붙여넣고,
echo   대괄호 부분만 바꿔주세요.
echo.
echo   --------------------------------------------
echo.
echo     쇼핑쇼츠 만들어줘.
echo     상품은 [상품명] 이고
echo     쿠팡 링크는 [파트너스 링크] 야.
echo.
echo     소재는 이 틱톡 링크들 써줘:
echo     [링크 붙여넣기]
echo.
echo   --------------------------------------------
echo.
echo   완성본이 나오는 곳:
echo   remotion-project\out\shorts.mp4
echo.
echo   아무 키나 누르면 이 자리에서 클로드코드가 열립니다.
pause >nul

call claude

echo.
echo   클로드코드가 종료되었습니다.
pause
exit /b 0


:NOCLAUDE
echo.
echo   클로드코드가 실행되지 않습니다.
echo.
echo   설치.bat 을 먼저 실행해 주세요.
echo   직접 깔려면 아래를 실행하세요.
echo     npm install -g @anthropic-ai/claude-code
echo.
pause
exit /b 1
