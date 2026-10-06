"""Build a printable PDF of the delivery script (1차 샘플).

Converts shinjh-serum-01_납품대본.md to a print-styled HTML page (A4 landscape,
scene image strip under each version's script) and prints it to PDF with
headless Chromium via Playwright.

    python docs/beauty-shorts/build_print.py --fonts <dir with bhs.ttf, noto400.ttf, noto700.ttf>
"""
import argparse
import datetime as dt
import html
import re
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
MD = HERE / "shinjh-serum-01_납품대본.md"
FRAMES = HERE / "examples" / "frames"
OUT = HERE / "shinjh-serum-01_납품대본_1차샘플.pdf"
TIMES = {"A": ["0:00", "0:03", "0:06", "0:10", "0:15", "0:20"], "B": ["0:00", "0:03", "0:07", "0:12", "0:20"], "C": ["0:00", "0:03", "0:10", "0:20"]}


def inline(t):
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t


def table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, body = cells[0], cells[2:]
    out = ["<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"]
    for r in body:
        out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def strip(v):
    items = "".join(
        f'<figure><img src="{(FRAMES / f"{v}{k + 1}.jpg").as_uri()}" alt=""><figcaption>{k + 1}번 · {t}</figcaption></figure>'
        for k, t in enumerate(TIMES[v]))
    return f'<div class="strip"><p class="cap">{v}안 장면 시안 — 고정 모델 실사(얼굴 장면) · 일러스트(제품·손 장면)</p><div class="frames">{items}</div></div>'


def convert(md):
    lines, out, i, cur_v = md.split("\n"), [], 0, None
    lst = None  # "ul" | "chk"
    def close_list():
        nonlocal lst
        if lst:
            out.append("</ul>")
            lst = None
    while i < len(lines):
        l = lines[i]
        if l.startswith("|"):
            close_list()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i]); i += 1
            out.append(table(rows))
            if cur_v:
                out.append(strip(cur_v)); cur_v = None
            continue
        if l.startswith("```"):
            close_list(); i += 1; buf = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(html.escape(lines[i])); i += 1
            out.append("<pre>" + "\n".join(buf) + "</pre>"); i += 1; continue
        m_chk = re.match(r"^\s*- \[ \] (.*)", l)
        m_li = re.match(r"^(\s*)- (.*)", l)
        if m_chk or m_li:
            kind = "chk" if m_chk else "ul"
            if lst != kind:
                close_list(); out.append(f'<ul class="{kind}">'); lst = kind
            if m_chk:
                out.append(f"<li>{inline(m_chk.group(1))}</li>")
            else:
                cls = ' class="sub"' if m_li.group(1) else ""
                out.append(f"<li{cls}>{inline(m_li.group(2))}</li>")
            i += 1; continue
        close_list()
        if l.startswith("# "):
            out.append(f"<h1>{inline(l[2:])}</h1>")
        elif l.startswith("## "):
            m = re.match(r"^## \d+\. ([ABC])안", l)
            cur_v = m.group(1) if m else None
            cls = ' class="ver"' if m else ""
            out.append(f"<h2{cls}>{inline(l[3:])}</h2>")
        elif l.startswith("> "):
            out.append(f"<blockquote>{inline(l[2:])}</blockquote>")
        elif l.startswith("---"):
            out.append("<hr>")
        elif l.strip():
            out.append(f"<p>{inline(l)}</p>")
        i += 1
    close_list()
    return "\n".join(out)


CSS = """
@font-face { font-family: Doc; src: url(%(fonts)s/noto400.ttf); font-weight: 400; }
@font-face { font-family: Doc; src: url(%(fonts)s/noto700.ttf); font-weight: 700; }
@font-face { font-family: Head; src: url(%(fonts)s/bhs.ttf); }
@page { size: A4 landscape; margin: 11mm 12mm 13mm; }
* { box-sizing: border-box; }
body { font-family: Doc, sans-serif; font-size: 9.6pt; line-height: 1.5; color: #231a1f; margin: 0; }
.band { display: flex; justify-content: space-between; align-items: center; border-bottom: 2.5px solid #ae2f5a; padding-bottom: 6px; margin-bottom: 10px; }
.band .tag { font-family: Head; font-size: 13pt; color: #fff; background: #ae2f5a; padding: 3px 12px; border-radius: 4px; }
.band .meta { font-size: 8.5pt; color: #74636b; }
h1 { font-family: Head; font-weight: 400; font-size: 20pt; color: #8e244d; margin: 4px 0 6px; }
h2 { font-family: Head; font-weight: 400; font-size: 14pt; color: #8e244d; margin: 14px 0 6px; break-after: avoid; }
p { margin: 3px 0; }
blockquote { margin: 4px 0; padding: 4px 10px; border-left: 3px solid #d81b60; color: #555; font-style: italic; }
ul { margin: 3px 0 6px; padding-left: 18px; }
li.sub { margin-left: 18px; list-style: circle; }
ul.chk { list-style: none; padding-left: 4px; }
ul.chk li::before { content: "☐  "; }
code { font-family: Doc, sans-serif; color: #c2185b; font-size: 9pt; }
pre { background: #f4f1f2; padding: 8px 10px; border-radius: 4px; font-family: Doc, sans-serif; white-space: pre-wrap; font-size: 9pt; }
hr { border: 0; border-top: 1px solid #ddd; margin: 10px 0; }
table { width: 100%%; border-collapse: collapse; margin: 6px 0 8px; font-size: 9pt; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
th { background: #f8e1ea; text-align: left; font-weight: 700; }
th, td { border: 1px solid #c9bcc2; padding: 4px 6px; vertical-align: top; }
.strip { break-inside: avoid; margin: 6px 0 4px; }
.strip .cap { font-weight: 700; color: #8e244d; font-size: 9pt; margin-bottom: 4px; }
.frames { display: flex; gap: 8px; }
.frames figure { margin: 0; width: 26mm; text-align: center; }
.frames img { width: 26mm; height: 46.2mm; object-fit: cover; border-radius: 3px; border: 1px solid #ddd; }
.frames figcaption { font-size: 7.5pt; color: #74636b; }
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True, help="directory with bhs.ttf, noto400.ttf, noto700.ttf")
    a = ap.parse_args()
    fonts = Path(a.fonts).resolve().as_uri()
    body = convert(MD.read_text(encoding="utf-8"))
    today = dt.date.today().strftime("%Y.%m.%d")
    page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>뷰티쇼츠 납품 대본 1차 샘플</title>
<style>{CSS % {"fonts": fonts}}</style></head><body>
<div class="band"><span class="tag">1차 샘플</span><span class="meta">수분 세럼 ABC · shinjh-serum-01 · 출력일 {today} · 실제 상품 정보 확정 전 시안</span></div>
{body}</body></html>"""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "print.html"
        src.write_text(page, encoding="utf-8")
        js = f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto({src.as_uri()!r}, {{ waitUntil: 'load' }});
  await p.evaluate(() => document.fonts.ready);
  await p.pdf({{ path: {str(OUT)!r}, preferCSSPageSize: true, printBackground: true,
    displayHeaderFooter: true, headerTemplate: '<span></span>',
    footerTemplate: '<div style="width:100%;font-size:8px;color:#888;text-align:center">뷰티쇼츠 납품 대본 1차 샘플 · <span class="pageNumber"></span> / <span class="totalPages"></span></div>' }});
  await b.close();
}})();"""
        (Path(tmp) / "pdf.js").write_text(js, encoding="utf-8")
        subprocess.run(["node", str(Path(tmp) / "pdf.js")], check=True)
    print(OUT)


if __name__ == "__main__":
    main()
