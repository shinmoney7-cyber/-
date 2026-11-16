// 검수: 자막이 뜬 직후 시점의 프레임을 뽑아 가로로 붙인다.
//
//   node tools/qc.js
//
// 결과: work/qc/row0.jpg, row1.jpg …  → 직접 열어서 자막과 화면이 맞는지 확인한다.
// 어긋나면 대본이 아니라 cuts.json의 씬 순서를 바꾸는 게 빠르다.
const fs = require("fs");
const path = require("path");
const { ROOT, PROJ, die, ff, readJson, ensure } = require("./lib");

const PER_ROW = 5;
const OFFSET = 0.45;   // 자막이 뜨고 팝업 애니메이션이 끝난 뒤

const MP4 = path.join(PROJ, "out", "shorts.mp4");
const QC = path.join(ROOT, "work", "qc");

if (!fs.existsSync(MP4)) {
  die(`${MP4} 가 없습니다. 먼저 렌더하세요:\n` +
      "        cd remotion-project && npm run render:data");
}

const caps = readJson(path.join(PROJ, "src", "data", "product.json")).captions;
if (!caps || !caps.length) {
  die("product.json에 captions가 비어 있습니다. node tools/tighten.js 를 먼저 실행하세요.");
}

ensure(QC);

const shots = caps.map((c, i) => {
  const f = path.join(QC, `f${String(i).padStart(2, "0")}.png`);
  ff("ffmpeg", ["-hide_banner", "-v", "error", "-y", "-ss", String(c.start + OFFSET),
                "-i", MP4, "-frames:v", "1", "-vf", "scale=260:-1", f]);
  return f;
});

const rows = [];
for (let i = 0; i < shots.length; i += PER_ROW) rows.push(shots.slice(i, i + PER_ROW));

rows.forEach((chunk, n) => {
  const args = ["-hide_banner", "-v", "error", "-y"];
  for (const f of chunk) args.push("-i", f);
  args.push("-filter_complex", `hstack=inputs=${chunk.length}`, path.join(QC, `row${n}.jpg`));
  ff("ffmpeg", args);
});

console.log(`자막 ${caps.length}개 · ${rows.length}줄 생성 → work/qc/`);
rows.forEach((_, n) => console.log(`  work/qc/row${n}.jpg`));
console.log("\n이 이미지를 열어서 자막과 화면이 맞는지 직접 확인하세요.");
