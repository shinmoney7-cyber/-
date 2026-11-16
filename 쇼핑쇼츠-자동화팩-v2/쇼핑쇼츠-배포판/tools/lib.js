// 공용 헬퍼. 모든 도구가 여기를 거쳐 ffmpeg/ffprobe를 부른다.
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const ROOT = path.dirname(__dirname);
const TOOLS = path.join(ROOT, "tools");
const PROJ = path.join(ROOT, "remotion-project");
const WORK = path.join(ROOT, "work");

// 실행 파일이 "있는지"가 아니라 "실제로 돌아가는지"를 본다.
// 윈도우는 파이썬처럼 실행되지 않는 껍데기(스토어 스텁)를 PATH에 심어두기 때문에
// 존재 여부만 보면 있다고 착각한다. 그래서 반드시 한 번 실행해 본다.
function probe(exe, args) {
  const r = spawnSync(exe, args, { encoding: "utf8", windowsHide: true });
  if (r.error || r.status !== 0) return null;
  return ((r.stdout || "") + (r.stderr || "")).trim().split(/\r?\n/)[0] || "(버전 미상)";
}

function die(msg) {
  console.error("\n[중단] " + msg + "\n");
  process.exit(1);
}

// ffmpeg는 진행 로그를 stderr로 보내고 종료코드는 0이다.
// stderr까지 받아야 silencedetect 같은 결과를 읽을 수 있다.
function ff(exe, args, { capture = false } = {}) {
  const r = spawnSync(exe, args, {
    encoding: "utf8",
    maxBuffer: 1 << 26,
    windowsHide: true,
    stdio: capture ? ["ignore", "pipe", "pipe"] : ["ignore", "pipe", "pipe"],
  });
  if (r.error) {
    die(`${exe} 를 실행하지 못했습니다. 설치.bat 을 다시 실행해 ffmpeg를 설치하세요.\n` + r.error.message);
  }
  const out = (r.stdout || "") + (r.stderr || "");
  if (r.status !== 0) {
    die(`${exe} 가 오류로 끝났습니다.\n${out.trim().split(/\r?\n/).slice(-12).join("\n")}`);
  }
  return out;
}

function duration(file) {
  const out = ff("ffprobe", ["-v", "error", "-show_entries", "format=duration",
                             "-of", "csv=p=0", file]).trim();
  const v = parseFloat(out);
  if (!isFinite(v)) die(`길이를 못 읽었습니다: ${file}`);
  return v;
}

const readJson = (f) => JSON.parse(fs.readFileSync(f, "utf8"));
const writeJson = (f, o) => fs.writeFileSync(f, JSON.stringify(o, null, 2) + "\n", "utf8");
const ensure = (d) => fs.mkdirSync(d, { recursive: true });

module.exports = { ROOT, TOOLS, PROJ, WORK, probe, die, ff, duration, readJson, writeJson, ensure };
