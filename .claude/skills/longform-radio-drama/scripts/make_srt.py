#!/usr/bin/env python3
"""Vrew 포맷 대본 → SRT 자막 초안. 설치 불필요 (python3 표준 라이브러리만 사용).

사용법: python3 make_srt.py 대본.txt 출력.srt [--cpm 500] [--pause 0.5]

- `[배역]` 표시와 `## ACT` 같은 제목 줄은 자막에서 뺀다.
- `[BGM ...]` 줄은 그대로 한 블록으로 넣는다 (음악 큐).
- 1줄 최대 15자, 1블록 최대 2줄.
- 시간은 낭독 속도(--cpm, 분당 자수)로 계산하고, 대본 한 줄이 끝날 때마다 --pause 초를 쉰다.
실제 음성과 맞춘 최종 자막은 Vrew에서 내보낸 SRT를 쓴다. 이 스크립트는 초안·분량 확인용이다.
"""
import argparse
import re

LINE_MAX = 15
ROLE = re.compile(r"^\s*\[(?!BGM)[^\]]*\]\s*")
HEADER = re.compile(r"^\s*#")


def wrap(text):
    """공백 기준으로 15자 이하 줄로 나눈다. 15자보다 긴 낱말은 잘라서 넣는다."""
    lines, cur = [], ""
    for word in text.split():
        while len(word) > LINE_MAX:
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(word[:LINE_MAX])
            word = word[LINE_MAX:]
        if not word:
            continue
        cand = f"{cur} {word}" if cur else word
        if len(cand) <= LINE_MAX:
            cur = cand
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def ts(sec):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def build(text, cpm, pause):
    cps = cpm / 60
    blocks, t = [], 0.0
    for raw in text.splitlines():
        if not raw.strip() or HEADER.match(raw):
            continue
        body = ROLE.sub("", raw).strip()
        if not body:
            continue
        lines = [body] if body.startswith("[BGM") else wrap(body)
        for i in range(0, len(lines), 2):
            chunk = lines[i:i + 2]
            dur = max(1.0, sum(len(x) for x in chunk) / cps)
            blocks.append((t, t + dur, "\n".join(chunk)))
            t += dur
        t += pause
    return blocks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("out")
    ap.add_argument("--cpm", type=float, default=500, help="분당 자수 (기본 500)")
    ap.add_argument("--pause", type=float, default=0.5, help="대본 줄 사이 쉼(초)")
    a = ap.parse_args()
    with open(a.script, encoding="utf-8") as f:
        blocks = build(f.read(), a.cpm, a.pause)
    with open(a.out, "w", encoding="utf-8") as f:
        for n, (s, e, txt) in enumerate(blocks, 1):
            f.write(f"{n}\n{ts(s)} --> {ts(e)}\n{txt}\n\n")
    end = blocks[-1][1] if blocks else 0
    print(f"블록 {len(blocks)}개, 총 길이 {ts(end)}")


if __name__ == "__main__":
    main()
