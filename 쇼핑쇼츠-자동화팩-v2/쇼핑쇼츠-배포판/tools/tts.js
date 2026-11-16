// 나레이션 1회 합성 + 자막 시작시각 실측.
//
//   node tools/tts.js
//   node tools/tts.js --voice ko-KR-InJoonNeural --rate +5%
//
// 대본.txt(한 줄 = 자막 한 줄)를 읽어 한 번에 합성한다.
// 줄마다 따로 합성하면 문장 흐름(프로소디)이 끊겨 어색해지므로 반드시 한 번에 부른다.
// 결과: work/vo_raw.mp3, work/timings.json
const fs = require("fs");
const path = require("path");
const { ROOT, TOOLS, WORK, die, ensure, writeJson } = require("./lib");

let MsEdgeTTS, OUTPUT_FORMAT;
try {
  ({ MsEdgeTTS, OUTPUT_FORMAT } = require("msedge-tts"));
} catch {
  die("나레이션 음성 모듈(msedge-tts)이 없습니다.\n" +
      "        설치.bat 을 다시 실행하거나, tools 폴더에서 npm install 을 하세요.");
}

const argv = process.argv.slice(2);
const opt = (name, def) => {
  const i = argv.indexOf(name);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : def;
};
const VOICE = opt("--voice", "ko-KR-SunHiNeural");
const RATE = opt("--rate", "+8%");
const SCRIPT = opt("--script", path.join(ROOT, "대본.txt"));

if (!fs.existsSync(SCRIPT)) die(`대본 파일이 없습니다: ${SCRIPT}`);

const CAPTIONS = fs.readFileSync(SCRIPT, "utf8")
  .replace(/^﻿/, "")   // 메모장이 붙이는 BOM 제거
  .split(/\r?\n/)
  .map((s) => s.trim())
  .filter((s) => s && !s.startsWith("#"));

if (!CAPTIONS.length) die("대본.txt가 비어 있습니다. 자막 한 줄당 한 행으로 써주세요.");

// 자막 경계를 찾을 때 쓰는 정규화: 문장부호·공백을 지운 순수 글자.
// Edge 음성이 어절을 어떻게 쪼개든 글자 수 누적으로 맞추면 어긋나지 않는다.
const norm = (s) => s.replace(/[\s.,!?~·…"'"'()\[\]\-]/g, "");

console.log(`자막 ${CAPTIONS.length}줄 · 보이스 ${VOICE} · 속도 ${RATE}`);

async function main() {
  const tts = new MsEdgeTTS();
  await tts.setMetadata(VOICE, OUTPUT_FORMAT.AUDIO_24KHZ_48KBITRATE_MONO_MP3, {
    wordBoundaryEnabled: true,
  });

  const { audioStream, metadataStream } = tts.toStream(CAPTIONS.join(" "), { rate: RATE });

  ensure(WORK);
  const audioPath = path.join(WORK, "vo_raw.mp3");
  const out = fs.createWriteStream(audioPath);
  audioStream.pipe(out);

  // metadata 스트림은 여러 줄 pretty JSON이 이어서 흘러나오고 end 이벤트를 안 보낸다.
  // → 중괄호 깊이로 객체 경계를 직접 잘라낸다.
  const words = [];
  let buf = "", depth = 0, start = -1;
  metadataStream.on("data", (chunk) => {
    const s = chunk.toString();
    for (const ch of s) {
      if (ch === "{") { if (depth === 0) start = buf.length; depth++; }
      buf += ch;
      if (ch === "}") {
        depth--;
        if (depth === 0 && start >= 0) {
          const raw = buf.slice(start);
          buf = ""; start = -1;
          try {
            for (const m of JSON.parse(raw).Metadata ?? []) {
              if (m.Type !== "WordBoundary") continue;
              words.push({ text: m.Data.text.Text, start: m.Data.Offset / 1e7, dur: m.Data.Duration / 1e7 });
            }
          } catch { /* 조각난 객체는 무시 */ }
        }
      }
    }
  });

  await new Promise((res, rej) => {
    out.on("finish", res);
    out.on("error", rej);
    audioStream.on("error", rej);
  });
  // 오디오가 끝난 뒤에도 메타데이터가 몇 개 늦게 도착한다
  await new Promise((r) => setTimeout(r, 500));

  if (!fs.statSync(audioPath).size) {
    die("음성이 생성되지 않았습니다. 인터넷 연결과 보이스 이름을 확인하세요.");
  }
  if (!words.length) {
    die("단어 타임스탬프를 못 받았습니다. 잠시 뒤 다시 실행해 보세요.");
  }

  // 정규화 글자 수를 누적해 각 자막의 시작 시각을 찾는다
  const timings = [];
  let wi = 0, carry = 0;
  for (const cap of CAPTIONS) {
    const need = norm(cap).length;
    if (wi >= words.length) {
      timings.push({ text: cap, start: timings.at(-1)?.start ?? 0 });
      continue;
    }
    const startSec = words[wi].start;
    let got = 0;
    while (got < need && wi < words.length) {
      const avail = norm(words[wi].text).length - carry;
      if (got + avail <= need) { got += avail; carry = 0; wi++; }
      else { carry += need - got; got = need; }
    }
    timings.push({ text: cap, start: Number(startSec.toFixed(3)) });
  }
  timings[0].start = 0;   // 첫 자막은 영상 시작과 함께

  const last = words.at(-1);
  writeJson(path.join(WORK, "timings.json"), {
    voice: VOICE, rate: RATE,
    spokenEnd: Number((last.start + last.dur).toFixed(3)),
    captions: timings,
  });

  for (const t of timings) console.log(`${String(t.start.toFixed(3)).padStart(8)}  ${t.text}`);
  console.log(`\n단어 이벤트 ${words.length}개 · 마지막 발화 ${(last.start + last.dur).toFixed(3)}초`);
  console.log("→ 다음: node tools/tighten.js");
  process.exit(0);
}

main().catch((e) => die(String(e && e.message ? e.message : e)));
