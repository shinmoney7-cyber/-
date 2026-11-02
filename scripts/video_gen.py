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

# ── 2. 슬라이드 이미지 세트 생성 (9:16 레이아웃) ────────────
# 레이아웃:
#   [상단 0~280px]  썸네일 문구 + 진행바   ← 오른쪽 최상단에 [광고] 아주 작게
#   [중앙 280~1260px] 메인 콘텐츠 (카드 1/2 = 960px)
#   [하단 1260~1920px] 채널 로고
def make_slide(text: str, slide_num: int, total: int, size=(1080, 1920)) -> Path:
    W, H = size
    THUMB_H   = 280   # 썸네일 문구 영역
    CONTENT_H = 960   # 메인 콘텐츠 (H의 절반)
    # LOGO zone: THUMB_H + CONTENT_H ~ H = 1260 ~ 1920

    img = Image.new("RGB", (W, H), bg_rgb)
    draw = ImageDraw.Draw(img)

    # 전체 배경 그라디언트
    for y in range(H):
        ratio = y / H
        r = int(bg_rgb[0] + (accent_rgb[0] - bg_rgb[0]) * ratio * 0.18)
        g = int(bg_rgb[1] + (accent_rgb[1] - bg_rgb[1]) * ratio * 0.18)
        b = int(bg_rgb[2] + (accent_rgb[2] - bg_rgb[2]) * ratio * 0.18)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 썸네일 상단 어두운 오버레이
    for y in range(THUMB_H):
        alpha = int(180 * (1 - y / THUMB_H))
        r = max(0, bg_rgb[0] - 60)
        g = max(0, bg_rgb[1] - 60)
        b = max(0, bg_rgb[2] - 60)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    try:
        font_thumb = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", 70)
        font_main  = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", 62)
        font_sub   = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 44)
        font_logo  = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", 54)
        font_ad    = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 22)
    except Exception:
        font_thumb = font_main = font_sub = font_logo = font_ad = ImageFont.load_default()

    # ── [광고] 최상단 오른쪽 모서리, 최대한 작고 흐리게 ─────
    draw.text((W - 16, 18), "광고", fill=(160, 160, 160), font=font_ad, anchor="rt")

    # ── [상단 0~280px] 썸네일 문구 ───────────────────────────
    # 진행바 (최상단 8px)
    progress_w = int(W * (slide_num / total))
    draw.rectangle([(0, 0), (W, 8)], fill=(40, 40, 60))
    draw.rectangle([(0, 0), (progress_w, 8)], fill=accent_rgb)

    # 썸네일 문구: 1번 슬라이드는 훅, 나머지는 텍스트 첫 줄
    thumb_text = hook if slide_num == 1 else text.split("\n")[0].strip()
    # 16자 초과 시 줄바꿈
    if len(thumb_text) > 16:
        mid = len(thumb_text) // 2
        sp = thumb_text.rfind(" ", 0, mid + 4)
        sp = sp if sp > 0 else mid
        thumb_lines = [thumb_text[:sp].strip(), thumb_text[sp:].strip()]
    else:
        thumb_lines = [thumb_text]

    thumb_start_y = 60
    for i, tl in enumerate(thumb_lines):
        draw.text(
            (W // 2, thumb_start_y + i * 88), tl,
            fill=(255, 255, 255), font=font_thumb, anchor="mm",
            stroke_width=2, stroke_fill=(0, 0, 0),
        )

    # 슬라이드 번호 (우하단 of 썸네일 영역)
    draw.text(
        (W - 30, THUMB_H - 24), f"{slide_num}/{total}",
        fill=(160, 160, 180), font=font_ad, anchor="rm",
    )

    # ── [중앙 280~1260px] 메인 콘텐츠 패널 ─────────────────
    CONTENT_TOP = THUMB_H
    CONTENT_BOT = THUMB_H + CONTENT_H  # 1240
    panel_pad = 44

    draw.rounded_rectangle(
        [(panel_pad, CONTENT_TOP + 20), (W - panel_pad, CONTENT_BOT - 20)],
        radius=32, fill=(16, 16, 36),
    )
    # 악센트 테두리 라인
    draw.rounded_rectangle(
        [(panel_pad, CONTENT_TOP + 20), (W - panel_pad, CONTENT_BOT - 20)],
        radius=32, outline=accent_rgb, width=3,
    )

    lines = [l.strip() for l in text.split("\n") if l.strip()][:6]
    line_spacing = 108
    total_txt_h = len(lines) * line_spacing
    txt_start_y = CONTENT_TOP + (CONTENT_H - total_txt_h) // 2

    for i, line in enumerate(lines):
        y_pos = txt_start_y + i * line_spacing
        if i == 0:
            draw.text(
                (W // 2, y_pos), line,
                fill=(255, 230, 60), font=font_main, anchor="mm",
                stroke_width=1, stroke_fill=(0, 0, 0),
            )
        else:
            draw.text((W // 2, y_pos), line, fill=(210, 210, 235), font=font_sub, anchor="mm")

    # ── [하단 1260~1920px] 채널 로고 ────────────────────────
    LOGO_CENTER_Y = CONTENT_BOT + (H - CONTENT_BOT) // 2  # ≈ 1590

    badge_half_w = 260
    draw.rounded_rectangle(
        [(W // 2 - badge_half_w, LOGO_CENTER_Y - 50),
         (W // 2 + badge_half_w, LOGO_CENTER_Y + 50)],
        radius=44, fill=accent_rgb,
    )
    draw.text((W // 2, LOGO_CENTER_Y), account["name"], fill=(0, 0, 0), font=font_logo, anchor="mm")

    # 로고 하단 인스타 CTA
    handle = account.get("handle", "")
    cta_url = f"@{handle}" if handle else content.get("cta", "무료 사주 상담")
    draw.text(
        (W // 2, LOGO_CENTER_Y + 100), f"📲 인스타 팔로우 → {cta_url}",
        fill=(160, 160, 190), font=font_ad, anchor="mm",
    )

    out = OUT_DIR / f"slide_v_{slide_num:02d}_{TODAY_STR}.png"
    img.save(str(out), "PNG")
    return out

# ── 3. YouTube Shorts 썸네일 생성 (9:16) ─────────────────────
# Shorts/세로형 콘텐츠 전용 — 동일한 9:16 레이아웃 적용
def make_youtube_thumbnail() -> Path:
    W, H = 1080, 1920
    THUMB_H   = 280
    CONTENT_H = 960
    img = Image.new("RGB", (W, H), bg_rgb)
    draw = ImageDraw.Draw(img)

    for y in range(H):
        ratio = y / H
        r = int(bg_rgb[0] + (accent_rgb[0] - bg_rgb[0]) * ratio * 0.2)
        g = int(bg_rgb[1] + (accent_rgb[1] - bg_rgb[1]) * ratio * 0.2)
        b = int(bg_rgb[2] + (accent_rgb[2] - bg_rgb[2]) * ratio * 0.2)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 썸네일 상단 어두운 오버레이
    for y in range(THUMB_H):
        r = max(0, bg_rgb[0] - 70)
        g = max(0, bg_rgb[1] - 70)
        b = max(0, bg_rgb[2] - 70)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    try:
        font_big  = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", 80)
        font_med  = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", 60)
        font_sub  = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 44)
        font_logo = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", 54)
        font_ad   = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 22)
    except Exception:
        font_big = font_med = font_sub = font_logo = font_ad = ImageFont.load_default()

    # [광고] 최상단 오른쪽 모서리
    draw.text((W - 16, 18), "광고", fill=(160, 160, 160), font=font_ad, anchor="rt")

    # [상단] 썸네일 문구 (훅)
    draw.rectangle([(0, 0), (W, 8)], fill=accent_rgb)
    thumb_lines = [hook] if len(hook) <= 16 else [hook[:len(hook)//2], hook[len(hook)//2:]]
    for i, tl in enumerate(thumb_lines):
        draw.text(
            (W // 2, 60 + i * 90), tl,
            fill=(255, 255, 255), font=font_big, anchor="mm",
            stroke_width=2, stroke_fill=(0, 0, 0),
        )

    # [중앙 280~1240px] 콘텐츠
    CONTENT_TOP = THUMB_H
    CONTENT_BOT = THUMB_H + CONTENT_H
    draw.rounded_rectangle(
        [(44, CONTENT_TOP + 20), (W - 44, CONTENT_BOT - 20)],
        radius=32, fill=(16, 16, 36),
    )
    draw.rounded_rectangle(
        [(44, CONTENT_TOP + 20), (W - 44, CONTENT_BOT - 20)],
        radius=32, outline=accent_rgb, width=4,
    )

    # 테마 + 메인 텍스트
    main_text = content.get("main_text", "").split("\n")
    preview_lines = [theme] + [l.strip() for l in main_text if l.strip()][:4]
    line_sp = 108
    tot_h = len(preview_lines) * line_sp
    ty = CONTENT_TOP + (CONTENT_H - tot_h) // 2
    for i, ln in enumerate(preview_lines):
        clr = (255, 230, 60) if i == 0 else (210, 210, 235)
        fn  = font_med if i == 0 else font_sub
        draw.text((W // 2, ty + i * line_sp), ln, fill=clr, font=fn, anchor="mm")

    # [하단] 채널 로고
    LOGO_Y = CONTENT_BOT + (H - CONTENT_BOT) // 2
    draw.rounded_rectangle(
        [(W // 2 - 260, LOGO_Y - 50), (W // 2 + 260, LOGO_Y + 50)],
        radius=44, fill=accent_rgb,
    )
    draw.text((W // 2, LOGO_Y), account["name"], fill=(0, 0, 0), font=font_logo, anchor="mm")
    _handle = account.get("handle", "")
    _cta = f"@{_handle}" if _handle else content.get("cta", "무료 사주 상담")
    draw.text(
        (W // 2, LOGO_Y + 100), f"📲 인스타 팔로우 → {_cta}",
        fill=(160, 160, 190), font=font_ad, anchor="mm",
    )

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
