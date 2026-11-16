@echo off
title 쇼핑쇼츠 자동화 팩 - 설치
cd /d "%~dp0"

echo.
echo   ============================================
echo     쇼핑쇼츠 자동화 팩 - 자동 설치
echo   ============================================
echo.
echo   필요한 프로그램을 자동으로 설치합니다.
echo   중간에 파란 창이나 허용 창이 뜨면 "예"를 눌러주세요.
echo.

rem OneDrive 안이면 동기화 때문에 렌더가 실패할 때가 있어 미리 알린다.
rem 외부 명령을 쓰지 않도록 문자열 치환으로 검사한다.
if not "%CD%"=="%CD:OneDrive=%" echo   [주의] 이 폴더가 OneDrive 안에 있습니다.
if not "%CD%"=="%CD:OneDrive=%" echo          동기화 때문에 렌더가 실패할 때가 있습니다.
if not "%CD%"=="%CD:OneDrive=%" echo          C:\shorts 같은 곳으로 옮긴 뒤 실행하시길 권합니다.
if not "%CD%"=="%CD:OneDrive=%" echo.

pause
echo.

echo   [1/3] 기본 프로그램 확인
echo   --------------------------------------------
echo   ※ 설치 여부가 아니라 실제로 실행되는지 확인합니다.
echo.

set NEEDBASE=0

node -v >nul 2>&1
if errorlevel 1 (echo     [없음] Node.js & set NEEDBASE=1) else (echo     [OK]   Node.js)

ffmpeg -version >nul 2>&1
if errorlevel 1 (echo     [없음] ffmpeg & set NEEDBASE=1) else (echo     [OK]   ffmpeg)

yt-dlp --version >nul 2>&1
if errorlevel 1 (echo     [없음] yt-dlp & set NEEDBASE=1) else (echo     [OK]   yt-dlp)

echo.
if "%NEEDBASE%"=="0" goto DEPS


:BASE
where winget >nul 2>&1
if errorlevel 1 goto NOWINGET

echo   빠진 것을 설치합니다. 몇 분 걸립니다.
echo.

node -v >nul 2>&1
if errorlevel 1 echo     - Node.js 설치 중
if errorlevel 1 winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements

ffmpeg -version >nul 2>&1
if errorlevel 1 echo     - ffmpeg 설치 중
if errorlevel 1 winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements

yt-dlp --version >nul 2>&1
if errorlevel 1 echo     - yt-dlp 설치 중
if errorlevel 1 winget install -e --id yt-dlp.yt-dlp --accept-source-agreements --accept-package-agreements

echo.
echo   ============================================
echo     1단계 완료 - 창을 닫고 다시 실행하세요
echo   ============================================
echo.
echo   방금 설치한 프로그램은 새로 연 창에서만 인식됩니다.
echo   이 창을 닫고 설치.bat 을 한 번 더 더블클릭하세요.
echo.
pause
exit /b 0


:DEPS
echo   [2/3] 부가 프로그램 설치
echo   --------------------------------------------

call claude --version >nul 2>&1
if errorlevel 1 echo     - 클로드코드 설치 중
if errorlevel 1 call npm install -g @anthropic-ai/claude-code

call claude --version >nul 2>&1
if errorlevel 1 (echo     [실패] 클로드코드 - 아래 SEE1 참고) else (echo     [OK]   클로드코드)

echo     - 나레이션 음성 모듈 설치 중
pushd tools
call npm install --ignore-scripts --no-fund --no-audit
if errorlevel 1 goto FAILTOOLS
popd
echo     [OK]   나레이션 음성 모듈

echo     - 영상 렌더 패키지 설치 중. 2~5분 걸립니다...
pushd remotion-project
call npm install --no-fund --no-audit
if errorlevel 1 goto FAILPROJ
popd
echo     [OK]   영상 렌더 패키지

echo.
echo   [3/3] 최종 점검
echo   --------------------------------------------
node tools\check.js

echo.
echo   ============================================
echo     설치 끝
echo   ============================================
echo.
echo   위에 [없음]이 하나도 없으면 준비 완료입니다.
echo   시작.bat 을 더블클릭하면 시작합니다.
echo.
pause
exit /b 0


:NOWINGET
echo   이 컴퓨터는 자동 설치 도구 winget 을 쓸 수 없습니다.
echo   아래 3개를 직접 설치한 뒤 설치.bat 을 다시 실행하세요.
echo.
echo     1. Node.js LTS   https://nodejs.org
echo     2. ffmpeg        https://www.gyan.dev/ffmpeg/builds
echo     3. yt-dlp        https://github.com/yt-dlp/yt-dlp/releases
echo.
echo   ffmpeg 와 yt-dlp 는 압축을 푼 뒤 그 안의 폴더를
echo   환경 변수 Path 에 추가해야 합니다.
echo.
pause
exit /b 1


:FAILTOOLS
popd
echo.
echo     [실패] 나레이션 음성 모듈을 받지 못했습니다.
echo.
echo     원인은 보통 둘 중 하나입니다.
echo       - 인터넷이 끊겼거나 회사/학교 네트워크가 npm 을 막고 있음
echo       - 백신이 npm 을 차단함
echo.
echo     인터넷을 확인하고 설치.bat 을 다시 실행하세요.
echo.
pause
exit /b 1


:FAILPROJ
popd
echo.
echo     [실패] 영상 렌더 패키지를 받지 못했습니다.
echo.
echo     인터넷 연결을 확인하고 설치.bat 을 다시 실행하세요.
echo     이 폴더가 OneDrive 안에 있으면 C:\shorts 같은 곳으로
echo     옮긴 뒤 다시 실행하면 해결되는 경우가 많습니다.
echo.
pause
exit /b 1
