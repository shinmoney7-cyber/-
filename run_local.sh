#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# run_local.sh  —  로컬 PC에서 Inpock 링크카드 동기화 실행 스크립트
#
# 사전 준비:
#   1. .env.example 을 복사해 .env 생성 후 계정 정보 입력
#      cp .env.example .env
#   2. Python 의존성 설치
#      pip install -r requirements.txt
#   3. Playwright Chromium 설치 (로컬에 없는 경우)
#      playwright install chromium
#   4. data/products.json 에 실제 제품명과 쿠팡 URL 입력
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

INPUT="data/products.json"
HEADED="${HEADED:-false}"  # HEADED=true ./run_local.sh 으로 브라우저 창 표시

headed_flag=""
if [ "$HEADED" = "true" ]; then
  headed_flag="--headed"
fi

echo "═══════════════════════════════════════════════════"
echo " [1/2] Coupang 딥링크 생성 (mock 모드)"
echo "       실제 API 키 발급 후 COUPANG_API_MODE=live 설정"
echo "═══════════════════════════════════════════════════"
python -m shopping_shorts_sync deeplink generate \
  --input "$INPUT" \
  --dry-run

echo ""
echo "═══════════════════════════════════════════════════"
echo " [2/2] Inpock 링크카드 동기화 (harujin + shinjh)"
echo "═══════════════════════════════════════════════════"
python -m shopping_shorts_sync inpock sync \
  --input "$INPUT" \
  --live \
  $headed_flag

echo ""
echo "✓ 완료"
