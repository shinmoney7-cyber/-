// 나레이션 공백 축소 + 자막 타임스탬프 재계산 + 프로젝트 자동 반영.
//
//   node tools/tighten.js              # vo.mp3 + product.json 까지 자동 반영
//   node tools/tighten.js --no-apply   # work/ 에만 만들고 반영은 안 함
//
// Edge 음성은 문장 사이에 0.9초쯤 되는 긴 공백을 넣는다. 쇼츠에서는 늘어져 보이므로
// 공백을 GAP초만 남기고 잘라내고, 줄어든 만큼 자막 start를 앞으로 당긴다.
const fs = require("fs");
const path = require("path");
const { PROJ, WORK, die, ff, duration, readJson, writeJson, ensure } = require("./lib");

const GAP = 0.16;      // 문장 사이 남길 공백
const TAIL = 0.30;     // 맨 끝에 남길 여유
const NOISE = "-45dB";
const MIN_SIL = 0.20;

const NO_APPLY = process.argv.includes("--no-apply");
const src = path.join(WORK, "vo_raw.mp3");
const dst = path.join(WORK, "vo.mp3");

if (!fs.existsSync(src)) die(`${src} 가 없습니다. 먼저 node tools/tts.js 를 실행하세요.`);

const total = duration(src);

// 무음 검출. ffmpeg는 결과를 stderr로 보내고 종료코드는 0이다.
const log = ff("ffmpeg", ["-hide_banner", "-v", "info", "-i", src,
                          "-af", `silencedetect=noise=${NOISE}:d=${MIN_SIL}`, "-f", "null", "-"]);

const starts = [...log.matchAll(/silence_start:\s*(-?[\d.]+)/g)].map((m) => Math.max(0, parseFloat(m[1])));
const ends = [...log.matchAll(/silence_end:\s*([\d.]+)/g)].map((m) => parseFloat(m[1]));
if (ends.length < starts.length) ends.push(total);

// 잘라낼 구간 = 공백에서 GAP(마지막 공백은 TAIL)만 남긴 나머지
const cuts = [];
for (let i = 0; i < starts.length; i++) {
  const s = starts[i], e = ends[i];
  const keep = e >= total - 1e-3 ? TAIL : GAP;
  if (e - s > keep) cuts.push([s + keep, e]);
}

// 남길 구간 = 잘라낼 구간의 여집합
const keeps = [];
let cur = 0;
for (const [s, e] of cuts) {
  if (s > cur) keeps.push([cur, s]);
  cur = e;
}
if (cur < total) keeps.push([cur, total]);

if (!keeps.length) die("잘라낼 구간 계산에 실패했습니다. work/vo_raw.mp3 를 직접 들어보세요.");

const chains = keeps.map(([s, e], i) =>
  `[0:a]atrim=start=${s.toFixed(4)}:end=${e.toFixed(4)},asetpts=N/SR/TB[a${i}]`).join(";");
const concat = keeps.map((_, i) => `[a${i}]`).join("") + `concat=n=${keeps.length}:v=0:a=1[out]`;

ff("ffmpeg", ["-hide_banner", "-v", "error", "-y", "-i", src,
              "-filter_complex", `${chains};${concat}`, "-map", "[out]",
              "-c:a", "libmp3lame", "-b:a", "192k", dst]);

// 원본 시각 t를 잘라낸 뒤의 시각으로 옮긴다
const remap = (t) => {
  let removed = 0;
  for (const [s, e] of cuts) {
    if (t >= e) removed += e - s;
    else if (t > s) removed += t - s;
  }
  return Number((t - removed).toFixed(3));
};

const timingsPath = path.join(WORK, "timings.json");
if (!fs.existsSync(timingsPath)) die("work/timings.json 이 없습니다. node tools/tts.js 를 먼저 실행하세요.");
const caps = readJson(timingsPath).captions.map((c) => ({ text: c.text, start: remap(c.start) }));
caps[0].start = 0;

const newDur = duration(dst);
ensure(WORK);
writeJson(path.join(WORK, "captions_tight.json"),
          { narrationDuration: Number(newDur.toFixed(3)), captions: caps });

console.log(`${total.toFixed(3)}s -> ${newDur.toFixed(3)}s  (구간 ${cuts.length}개 ${(total - newDur).toFixed(3)}s 삭제)`);
for (const c of caps) console.log(`${String(c.start.toFixed(3)).padStart(8)}  ${c.text}`);

if (NO_APPLY) process.exit(0);

// --- 프로젝트에 자동 반영 -------------------------------------------------
const audioDir = path.join(PROJ, "public", "audio");
ensure(audioDir);
fs.copyFileSync(dst, path.join(audioDir, "vo.mp3"));

const pj = path.join(PROJ, "src", "data", "product.json");
const product = readJson(pj);
product.captions = caps;
product.narrationDuration = Number(newDur.toFixed(3));
writeJson(pj, product);

console.log("\n반영 완료:");
console.log("  remotion-project/public/audio/vo.mp3");
console.log("  remotion-project/src/data/product.json  (captions, narrationDuration)");
console.log(`\n→ 다음: tools/cuts.json 을 작성하고 node tools/cut.js`);
console.log(`   (씬 5개 기준 씬당 약 ${(newDur / 5).toFixed(2)}초)`);
