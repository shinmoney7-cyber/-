"""benchmark/*.json(잘 나가는 영상 분석 결과)을 studio.html의 BENCH 데이터로 넣는다.

    python docs/beauty-shorts/build_benchmark.py

분석 방법은 .claude/skills/beauty-hit-analysis/SKILL.md 참고.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
DIR = HERE / "benchmark"


def main():
    bench = {}
    for f in sorted(DIR.glob("*.json")):
        if f.name.startswith("_"):
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        bench[d["key"]] = d
    summary = DIR / "_summary.json"
    if summary.exists():
        bench["_summary"] = json.loads(summary.read_text(encoding="utf-8"))
    studio = HERE / "studio.html"
    s = studio.read_text(encoding="utf-8")
    data = json.dumps(bench, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    s, n = re.subn(r"/\*@BENCH\*/.*?/\*@BENCH_END\*/", lambda m: f"/*@BENCH*/{data}/*@BENCH_END*/", s, flags=re.S)
    assert n == 1, "studio.html에 BENCH 자리 표시가 없습니다"
    studio.write_text(s, encoding="utf-8")
    print(f"BENCH: {', '.join(k for k in bench if not k.startswith('_'))}")


if __name__ == "__main__":
    main()
