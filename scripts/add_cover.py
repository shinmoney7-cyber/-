#!/usr/bin/env python3
"""
FL PDF의 1페이지(사주톡톡 표지)를 사주마루 커버로 교체
사용법: python scripts/add_cover.py 원본.pdf [출력.pdf]
"""
import sys, subprocess, os
from pathlib import Path

# 의존성 확인
try:
    from pypdf import PdfWriter, PdfReader
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pypdf', '-q'])
    from pypdf import PdfWriter, PdfReader

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False

COVER_HTML = Path(__file__).parent.parent / 'pages' / 'cover-page.html'
COVER_PDF  = Path('/tmp/saju_maru_cover.pdf')


def render_cover_pdf():
    """커버 HTML → PDF 변환"""
    if not PLAYWRIGHT_OK:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'playwright', '-q'])
        subprocess.check_call([sys.executable, '-m', 'playwright', 'install', 'chromium'])
        from playwright.sync_api import sync_playwright

    from playwright.sync_api import sync_playwright
    _chromium = '/opt/pw-browsers/chromium'

    with sync_playwright() as p:
        browser = p.chromium.launch(
            **({"executable_path": _chromium} if os.path.exists(_chromium) else {}),
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage'],
        )
        page = browser.new_page()
        page.goto(f'file://{COVER_HTML.resolve()}', wait_until='networkidle')
        page.pdf(
            path=str(COVER_PDF),
            width='794px',
            height='1123px',
            print_background=True,
        )
        browser.close()
    print(f'[커버] PDF 생성 완료: {COVER_PDF}')


def replace_cover(input_pdf: str, output_pdf: str = None):
    input_path = Path(input_pdf)
    if not input_path.exists():
        print(f'[오류] 파일 없음: {input_pdf}')
        sys.exit(1)

    if output_pdf is None:
        output_pdf = str(input_path.parent / (input_path.stem + '_사주마루.pdf'))

    # 커버 PDF 생성 (캐시: 같은 날은 재사용)
    if not COVER_PDF.exists():
        render_cover_pdf()

    cover_reader = PdfReader(str(COVER_PDF))
    orig_reader  = PdfReader(input_pdf)

    writer = PdfWriter()

    # 1페이지: 사주마루 커버
    writer.add_page(cover_reader.pages[0])

    # 나머지 페이지: 원본 2페이지~끝
    for i in range(1, len(orig_reader.pages)):
        writer.add_page(orig_reader.pages[i])

    with open(output_pdf, 'wb') as f:
        writer.write(f)

    print(f'[완료] 저장됨: {output_pdf}')
    print(f'  원본 {len(orig_reader.pages)}페이지 → 커버 교체 후 {len(orig_reader.pages)}페이지')
    return output_pdf


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('사용법: python scripts/add_cover.py 원본.pdf [출력.pdf]')
        sys.exit(1)
    replace_cover(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
