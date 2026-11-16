// 환경 점검 — 쇼츠 제작에 필요한 게 다 있는지 확인한다.
//   node tools/check.js
const fs = require("fs");
const path = require("path");
const { PROJ, TOOLS, probe } = require("./lib");

const BINS = [
  ["Node.js", "node", ["-v"], "설치.bat 을 실행하세요."],
  ["npm", "npm", ["-v"], "Node.js를 설치하면 같이 깔립니다. 설치.bat 을 실행하세요."],
  ["ffmpeg", "ffmpeg", ["-version"], "winget install -e --id Gyan.FFmpeg   (설치 후 창을 새로 여세요)"],
  ["ffprobe", "ffprobe", ["-version"], "ffmpeg에 들어 있습니다. 위 ffmpeg를 설치하세요."],
  ["yt-dlp", "yt-dlp", ["--version"], "winget install -e --id yt-dlp.yt-dlp   (설치 후 창을 새로 여세요)"],
];

let ok = true;
const line = "=".repeat(52);
console.log(line);
console.log("  쇼핑쇼츠 환경 점검");
console.log(line + "\n");

for (const [name, exe, args, hint] of BINS) {
  // windows에서 npm은 npm.cmd라 셸을 거쳐야 한다.
  const isCmd = exe === "npm";
  const v = isCmd
    ? probe(process.env.ComSpec || "cmd.exe", ["/c", exe, ...args])
    : probe(exe, args);
  if (v) {
    console.log(`[OK]   ${name}  ${v.slice(0, 48)}`);
  } else {
    console.log(`[없음] ${name}`);
    console.log(`       → ${hint}`);
    ok = false;
  }
}

// 나레이션 음성 모듈
try {
  require.resolve("msedge-tts", { paths: [TOOLS] });
  console.log("[OK]   msedge-tts (나레이션 음성)");
} catch {
  console.log("[없음] msedge-tts (나레이션 음성)");
  console.log("       → cd tools && npm install");
  ok = false;
}

// 렌더 프로젝트 의존성
if (fs.existsSync(path.join(PROJ, "node_modules"))) {
  console.log("[OK]   remotion 패키지 설치됨");
} else {
  console.log("[없음] remotion 패키지");
  console.log("       → cd remotion-project && npm install   (최초 1회, 2~5분)");
  ok = false;
}

// 클로드코드 (없어도 도구는 돌아가므로 안내만)
const claude = probe(process.env.ComSpec || "cmd.exe", ["/c", "claude", "--version"]);
console.log(claude ? `[OK]   클로드코드  ${claude.slice(0, 48)}`
                   : "[안내] 클로드코드가 PATH에 없습니다 → npm install -g @anthropic-ai/claude-code");

console.log();
if (ok) {
  console.log("모두 준비됐습니다. 시작.bat 을 눌러 클로드코드에 상품명과 소스 링크를 주세요.");
} else {
  console.log("위에 [없음]으로 표시된 것을 먼저 설치하세요.");
  console.log("설치.bat 을 한 번 더 실행하면 대부분 해결됩니다.");
  console.log("그래도 남으면 클로드코드에 '없는 것 설치해줘' 라고 하세요.");
}
console.log();
process.exit(ok ? 0 : 1);
