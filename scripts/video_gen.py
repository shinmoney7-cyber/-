"""
수익 최대화 영상 생성기
edge-tts (MS Neural TTS) + ffmpeg로 전문 품질 숏폼 영상 생성
- TikTok/Reels용: 9:16 (1080×1920)
- YouTube Shorts용: 9:16 (1080×1920)
- YouTube 썸네일: 16:9 (1280×720)
- 네이버 클립용: 9:16
"""
import os, sys, json, asyncio, subprocess, tempfile, datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ── 환경 로드 ─────────────────────────────────────────────────
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

ACCOUNT_ID = os.environ.get("ACCOUNT_ID", "sm")
HOUR_KST = int(os.environ.get("HOUR_KST", "6"))
TODAY_STR = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d")

with open(Path(__file__).parent.parent / "data" / "accounts.json", encoding="utf-8") as f:
    config = json.load(f)
account = next(a for a in config["accounts"] if a["id"] == ACCOUNT_ID)

OUT_DIR = Path(__file__).parent / "sns_output" / ACCOUNT_ID
OUT_DIR.mkdir(parents=True, exist_ok=True)

meta_path = OUT_DIR / "meta.json"
if not meta_path.exists():
    meta_path = Path(__file__).parent / "sns_output" / "meta.json"

with open(meta_path, encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]
script = content.get("tiktok_script", content.get("youtube_script", ""))
hook = content.get("hook", "오늘의 운세")
theme = content.get("theme", "")
accent_hex = account["accent"].lstrip("#")
accent_rgb = tuple(int(accent_hex[i:i+2], 16) for i in (0, 2, 4))
bg_hex = account["bg"].lstrip("#")
bg_rgb = tuple(int(bg_hex[i:i+2], 16) for i in (0, 2, 4))

# ── TTS 음성 매핑 ─────────────────────────────────────────────
VOICES = {
    "sm":  "ko-KR-InJoonNeural",   # 사주마루: 남성, 권위있는
    "un":  "ko-KR-SunHiNeural",    # 사주보는언니: 여성, 따뜻한
    "s77": "ko-KR-HyunsuNeural",   # 사주마루77: 남성, 트렌디
}
VOICE = VOICES.get(ACCOUNT_ID, "ko-KR-SunHiNeural")

# ── 1. TTS 오디오 생성 ────────────────────────────────────────
async def generate_tts(text: str, output_path: str) -> bool:
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, VOICE, rate="+5%", volume="+10%")
        await communicate.save(output_path)
        return True
    except Exception as e:
        print(f"  ❌ TTS 오류: {e}")
        return False

# ── 2. 슬라이드 이미지 세트 생성 ────────────────────────────
def make_slide(text: str, slide_num: int, total: int, size=(1080, 1920)) -> Path:
    W, H = size
    img = Image.new("RGB", (W, H), bg_rgb)
    draw = ImageDraw.Draw(img)

    # 배경 그라디언트
    for y in range(H):
        ratio = y / H
        r = int(bg_rgb[0] + (accent_rgb[0] - bg_rgb[0]) * ratio * 0.15)
        g = int(bg_rgb[1] + (accent_rgb[1] - bg_rgb[1]) * ratio * 0.15)
        b = int(bg_rgb[2] + (accent_rgb[2] - bg_rgb[2]) * ratio * 0.15)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 상단 진행바
    progress_w = int(W * (slide_num / total))
    draw.rectangle([(0, 0), (W, 8)], fill=(60, 60, 80))
    draw.rectangle([(0, 0), (progress_w, 8)], fill=accent_rgb)

    # 계정명
    try:
        font_acc = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", 36)
        font_main = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", 68)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 40)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 30)
    except Exception:
        font_acc = font_main = font_sub = font_small = ImageFont.load_default()

    draw.text((W//2, 80), account["name"], fill=accent_rgb, font=font_acc, anchor="mm")
    draw.text((W//2, 130), f"{slide_num}/{total}", fill=(100, 100, 130), font=font_small, anchor="mm")

    # 메인 텍스트 (줄바꿈 처리)
    lines = [l.strip() for l in text.split("\n") if l.strip()][:5]
    start_y = H // 2 - len(lines) * 55
    for i, line in enumerate(lines):
        # 강조선
        if i == 0:
            draw.text((W//2, start_y + i*110), line, fill=(255, 255, 255), font=font_main, anchor="mm")
        else:
            draw.text((W//2, start_y + i*110), line, fill=(200, 200, 220), font=font_sub, anchor="mm")

    # 하단 CTA 박스
    cta = content.get("cta", "무료 상담 지금 예약")
    cta_y = H - 200
    draw.rounded_rectangle(
        [(W//2-280, cta_y-35), (W//2+280, cta_y+35)],
        radius=35, fill=accent_rgb
    )
    draw.text((W//2, cta_y), f"👉 {cta}", fill=(0, 0, 0), font=font_sub, anchor="mm")

    # URL
    draw.text((W//2, H-80), "forms.gle/t2sSNES5NYow77vz5", fill=(100, 100, 130), font=font_small, anchor="mm")

    out = OUT_DIR / f"slide_v_{slide_num:02d}_{TODAY_STR}.png"
    img.save(str(out), "PNG")
    return out

# ── 3. YouTube 썸네일 생성 (16:9) ────────────────────────────
def make_youtube_thumbnail() -> Path:
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), bg_rgb)
    draw = ImageDraw.Draw(img)

    # 강렬한 배경
    for y in range(H):
        ratio = y / H
        r = int(bg_rgb[0] * (1 - ratio * 0.5) + accent_rgb[0] * ratio * 0.3)
        g = int(bg_rgb[1] * (1 - ratio * 0.5) + accent_rgb[1] * ratio * 0.3)
        b = int(bg_rgb[2] * (1 - ratio * 0.5) + accent_rgb[2] * ratio * 0.3)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", 100)
        font_med = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", 56)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 40)
    except Exception:
        font_big = font_med = font_sm = ImageFont.load_default()

    # 강렬한 훅 (상단)
    draw.text((W//2, 140), hook, fill=(255, 255, 80), font=font_big, anchor="mm")

    # 테마
    draw.text((W//2, 280), theme, fill=(255, 255, 255), font=font_med, anchor="mm")

    # 계정명 배지
    badge_y = H - 100
    draw.rounded_rectangle([(40, badge_y-30), (340, badge_y+30)], radius=25, fill=accent_rgb)
    draw.text((190, badge_y), account["name"], fill=(0, 0, 0), font=font_sm, anchor="mm")

    # 무료 배지
    draw.rounded_rectangle([(W-340, badge_y-30), (W-40, badge_y+30)], radius=25, fill=(255, 50, 50))
    draw.text((W-190, badge_y), "🆓 무료 상담", fill=(255, 255, 255), font=font_sm, anchor="mm")

    out = OUT_DIR / f"thumbnail_yt_{TODAY_STR}.jpg"
    img.save(str(out), "JPEG", quality=95)
    return out

# ── 4. ffmpeg로 MP4 영상 생성 ────────────────────────────────
def create_video_ffmpeg(slide_paths: list[Path], audio_path: str, output_path: Path) -> bool:
    if not slide_paths:
        return False

    # 슬라이드 지속 시간 계산 (총 오디오 길이 / 슬라이드 수)
    try:
        probe = subprocess.run(
            ["ffprobe", "-i", audio_path, "-show_entries", "format=duration",
             "-v", "quiet", "-of", "csv=p=0"],
            capture_output=True, text=True, timeout=30
        )
        audio_duration = float(probe.stdout.strip() or "60")
    except Exception:
        audio_duration = 60.0

    slide_duration = max(audio_duration / len(slide_paths), 3.0)

    # 이미지 리스트 파일 생성
    list_file = OUT_DIR / "slide_list.txt"
    with open(list_file, "w") as f:
        for slide in slide_paths:
            f.write(f"file '{slide.resolve()}'\n")
            f.write(f"duration {slide_duration:.2f}\n")
        # 마지막 프레임 freeze
        if slide_paths:
            f.write(f"file '{slide_paths[-1].resolve()}'\n")

    # ffmpeg: 슬라이드쇼 + 오디오 + 자막 (Ken Burns 줌 효과)
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-i", audio_path,
        "-vf", (
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,"
            "zoompan=z='if(lte(zoom,1.0),1.05,max(1.001,zoom-0.0015))':d=125:s=1080x1920"
        ),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"  ffmpeg 오류: {result.stderr[-300:]}")
        # 심플 버전으로 재시도
        simple_cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart",
            str(output_path)
        ]
        result2 = subprocess.run(simple_cmd, capture_output=True, text=True, timeout=300)
        return result2.returncode == 0

    return True

# ── 메인 실행 ─────────────────────────────────────────────────
async def main():
    print(f"🎬 [{account['name']}] 영상 생성 시작")

    if not script:
        print("  ⚠️ 스크립트 없음 — 기본 훅으로 대체")
        tts_text = f"{hook}. {content.get('main_text', '')}. {content.get('cta', '')}"
    else:
        tts_text = script

    # 1. TTS 오디오
    audio_path = str(OUT_DIR / f"tts_{TODAY_STR}_{HOUR_KST:02d}h.mp3")
    print(f"  🎤 TTS 생성 ({VOICE})...")
    tts_ok = await generate_tts(tts_text, audio_path)
    if not tts_ok:
        audio_path = ""

    # 2. 슬라이드 이미지 (5장)
    print("  🖼️  슬라이드 이미지 생성...")
    slides_text = [
        f"{hook}",
        f"{content.get('main_text', '').split(chr(10))[0] if content.get('main_text') else theme}",
        f"{content.get('main_text', '').split(chr(10))[1] if len(content.get('main_text','').split(chr(10))) > 1 else '지금 바로 확인'}",
        f"🌟 오늘의 행운\n{content.get('lucky_element', '빨간색 · 숫자 7')}",
        f"📱 무료 상담\n{content.get('cta', '지금 예약하기')}",
    ]
    slide_paths = [make_slide(t, i+1, len(slides_text)) for i, t in enumerate(slides_text)]
    print(f"  ✅ 슬라이드 {len(slide_paths)}장 생성")

    # 3. YouTube 썸네일
    thumb_path = make_youtube_thumbnail()
    print(f"  ✅ 유튜브 썸네일: {thumb_path.name}")

    # 4. MP4 영상 생성
    if audio_path and Path(audio_path).exists():
        print("  🎬 MP4 영상 합성 중...")
        video_path = OUT_DIR / f"shorts_{TODAY_STR}_{HOUR_KST:02d}h.mp4"
        ok = create_video_ffmpeg(slide_paths, audio_path, video_path)
        if ok:
            size_mb = video_path.stat().st_size / 1024 / 1024
            print(f"  ✅ 영상 생성 완료: {video_path.name} ({size_mb:.1f}MB)")
            meta["video_path"] = str(video_path)
            meta["video_shorts"] = str(video_path)
        else:
            print("  ❌ 영상 생성 실패")
    else:
        print("  ⚠️ TTS 없이 영상 건너뜀")

    meta["thumbnail_youtube"] = str(thumb_path)
    meta["slides_vertical"] = [str(p) for p in slide_paths]

    # 영상 경로를 tiktok_output에도 복사 (tiktok_post.py 호환)
    tiktok_dir = Path(__file__).parent / "tiktok_output"
    tiktok_dir.mkdir(exist_ok=True)
    import shutil
    shutil.copy(str(meta_path.parent / "meta.json") if meta_path.parent != Path(__file__).parent/"sns_output" else str(meta_path), tiktok_dir / "meta.json")

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # 레거시 경로 sync
    legacy = Path(__file__).parent / "sns_output" / "meta.json"
    with open(legacy, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"✅ 영상 생성 완료")

asyncio.run(main())
