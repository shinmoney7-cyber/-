#!/usr/bin/env python3
"""대본 구간별 자수 검사. 설치 불필요 (python3 표준 라이브러리만 사용).

사용법: python3 count_chars.py 대본.txt
대본은 구간마다 `## HOOK`, `## ACT 1` ~ `## ACT 4`, `## OUTRO` 제목 줄로 나눈다.
자수는 공백 포함, `[배역]` 표시와 제목 줄은 뺀다. 미달 구간이 있으면 종료 코드 1.
"""
import re
import sys

# 구간 이름: (최소, 최대) — 최소는 목표의 95%
TARGETS = {
    "HOOK": (150, 200),
    "ACT 1": (7125, None),
    "ACT 2": (7125, None),
    "ACT 3": (7125, None),
    "ACT 4": (5700, None),
    "OUTRO": (1425, None),
}
TOTAL_MIN = 28500

ROLE = re.compile(r"^\s*\[[^\]]*\]\s*")
HEADER = re.compile(r"^\s*##\s*(HOOK|ACT\s*[1-4]|OUTRO)\b", re.IGNORECASE)


def count_sections(text):
    counts = {}
    current = None
    for line in text.splitlines():
        m = HEADER.match(line)
        if m:
            current = re.sub(r"ACT\s*", "ACT ", m.group(1).upper())
            counts.setdefault(current, 0)
            continue
        if current is None:
            continue
        counts[current] += len(ROLE.sub("", line).strip())
    return counts


def main():
    if len(sys.argv) != 2:
        sys.exit("사용법: python3 count_chars.py 대본.txt")
    with open(sys.argv[1], encoding="utf-8") as f:
        counts = count_sections(f.read())

    failed = False
    print(f"{'구간':<8}{'자수':>8}  판정")
    for name, (lo, hi) in TARGETS.items():
        n = counts.get(name)
        if n is None:
            print(f"{name:<8}{'-':>8}  ❌ 구간 없음")
            failed = True
            continue
        ok = n >= lo and (hi is None or n <= hi)
        failed |= not ok
        need = f"(목표 {lo}~{hi})" if hi else f"(최소 {lo})"
        print(f"{name:<8}{n:>8}  {'✅' if ok else '❌'} {need}")
    total = sum(counts.values())
    ok = total >= TOTAL_MIN
    failed |= not ok
    print(f"{'합계':<8}{total:>8}  {'✅' if ok else '❌'} (최소 {TOTAL_MIN})")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
