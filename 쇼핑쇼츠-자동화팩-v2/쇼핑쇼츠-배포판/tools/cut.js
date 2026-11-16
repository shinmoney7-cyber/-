// 소스 컷편집 → remotion-project/public/clips/01.mp4 …
//
//   node tools/cut.js
//   node tools/cut.js --cuts tools/cuts.json
//
// cuts.json에 적힌 대로 구간을 잘라 9:16 1080×1920으로 맞춘다.
// crop은 소스마다 다르다. 워터마크 위치를 프레임으로 실측한 뒤 적어야 한다.
const fs = require("fs");
const path = require("path");
const { ROOT, TOOLS, PROJ, die, ff, duration, readJson, ensure } = require("./lib");

const SCALE = "scale=1080:1920:flags=lanczos,fps=30,setsar=1";
const TMP = path.join(ROOT, "work", "cuts");
const OUT = path.join(PROJ, "public", "clips");

const i = process.argv.indexOf("--cuts");
const cutsPath = i >= 0 && process.argv[i + 1]
  ? path.resolve(process.argv[i + 1])
  : path.join(TOOLS, "cuts.json");

if (!fs.existsSync(cutsPath)) {
  die(`${cutsPath} 가 없습니다.\n` +
      "        tools/cuts.example.json 을 복사해서 cuts.json 으로 만들고 채워주세요.");
}

const cfg = readJson(cutsPath);
const sources = cfg.sources || {};
const scenes = cfg.scenes || {};
if (!Object.keys(sources).length || !Object.keys(scenes).length) {
  die("cuts.json 에 sources 와 scenes 가 모두 있어야 합니다.");
}

// cuts.json의 경로는 tools/ 기준 상대경로로 적는다.
const resolve = (p) => (path.isAbsolute(p) ? p : path.join(TOOLS, p));

for (const [key, s] of Object.entries(sources)) {
  const f = resolve(s.file);
  if (!fs.existsSync(f)) die(`소스 파일이 없습니다: ${f}  (sources.${key})`);
}

ensure(TMP);
ensure(OUT);

for (const scene of Object.keys(scenes).sort()) {
  const segs = scenes[scene];
  if (!Array.isArray(segs) || !segs.length) die(`scenes.${scene} 가 비어 있습니다.`);

  const parts = [];
  segs.forEach((seg, k) => {
    const s = sources[seg.src];
    if (!s) die(`scenes.${scene} 의 src "${seg.src}" 가 sources 에 없습니다.`);
    const vf = s.crop ? `${s.crop},${SCALE}` : SCALE;
    const pf = path.join(TMP, `${scene}_${k}.mp4`);
    ff("ffmpeg", ["-hide_banner", "-v", "error", "-y",
                  "-ss", String(seg.ss), "-i", resolve(s.file), "-t", String(seg.t),
                  "-vf", vf, "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                  "-pix_fmt", "yuv420p", "-an", "-r", "30", pf]);
    parts.push(pf);
  });

  const final = path.join(OUT, `${scene}.mp4`);
  if (parts.length === 1) {
    fs.copyFileSync(parts[0], final);
  } else {
    const lst = path.join(TMP, `${scene}.txt`);
    // concat 목록은 슬래시 경로여야 한다. 윈도우 역슬래시는 이스케이프로 먹힌다.
    const slash = (p) => p.split(path.sep).join("/");
    fs.writeFileSync(lst, parts.map((p) => `file '${slash(p)}'`).join("\n") + "\n", "utf8");
    // -c copy 로 붙이면 구간 경계에서 PTS가 튀어 Remotion이
    // "No frame found at position" 으로 죽는다. 반드시 다시 인코딩한다.
    ff("ffmpeg", ["-hide_banner", "-v", "error", "-y", "-f", "concat", "-safe", "0",
                  "-i", lst, "-fps_mode", "cfr", "-r", "30",
                  "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                  "-pix_fmt", "yuv420p", "-g", "30", "-an", final]);
  }
  console.log(`${scene}.mp4  ${duration(final).toFixed(3)}s`);
}

console.log(`\n${Object.keys(scenes).length}개 씬 완료 → remotion-project/public/clips/`);
console.log("→ 다음: product.json의 scenes 확인 후  cd remotion-project && npm run render:data");
