"""
유튜브 Shorts + 일반 영상 자동 업로드
- video_gen.py 생성 MP4 우선 사용
- 없으면 ffmpeg로 이미지→영상 변환
- SEO 최적화: 챕터, 자막, 엔드 카드 설명
필요: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN
"""
import os, json, requests, subprocess
from pathlib import Path

CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
ACCOUNT_ID = os.environ.get("ACCOUNT_ID", "sm")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    print("⚠️  YouTube API 미설정 — 건너뜀")
    exit(0)

meta_path = Path("scripts/sns_output") / ACCOUNT_ID / "meta.json"
if not meta_path.exists():
    meta_path = Path("scripts/sns_output/meta.json")

with open(meta_path, encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]

# 1. Access Token 갱신
token_res = requests.post("https://oauth2.googleapis.com/token", data={
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "refresh_token": REFRESH_TOKEN,
    "grant_type": "refresh_token",
})
access_token = token_res.json().get("access_token", "")
if not access_token:
    print("❌ YouTube 토큰 갱신 실패:", token_res.json())
    exit(1)

print("✅ YouTube 토큰 갱신 완료")

# 2. 영상 파일 결정
video_path = meta.get("video_shorts") or meta.get("video_path", "")
is_shorts = True

if not video_path or not Path(video_path).exists():
    # fallback: 이미지 → 60초 Shorts
    image_path = meta.get("image_path", "")
    if not image_path or not Path(image_path).exists():
        print("❌ 영상/이미지 없음 — 건너뜀")
        exit(0)

    video_path = image_path.replace(".jpg", "_yt.mp4").replace(".png", "_yt.mp4")
    result = subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", image_path,
        "-c:v", "libx264", "-t", "58", "-pix_fmt", "yuv420p",
        "-vf", "scale=1080:1920,format=yuv420p",
        "-movflags", "+faststart",
        video_path
    ], capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print("❌ ffmpeg 변환 실패:", result.stderr[-300:])
        exit(1)
    print(f"✅ 이미지→영상 변환: {Path(video_path).name}")

print(f"✅ 업로드 영상: {Path(video_path).name}")

# 3. SEO 최적화 메타데이터
account_name = meta.get("account", {}).get("name", "사주마루")
title = content.get("youtube_title", f"오늘의 운세 {meta.get('date', '')} | {account_name}")[:100]

# 수익화를 위한 SEO 최적화 설명
description_parts = [
    content.get("youtube_description", content.get("main_text", "")),
    "",
    "━━━━━━━━━━━━━━━━━━━━━━━━━━",
    "🔮 무료 사주 상담 예약: https://forms.gle/t2sSNES5NYow77vz5",
    "━━━━━━━━━━━━━━━━━━━━━━━━━━",
    "",
    "📌 이 영상에서는:",
    f"• {content.get('hook', '오늘의 운세 분석')}",
    f"• 행운의 요소: {content.get('lucky_element', '확인해보세요')}",
    "• 무료 사주 상담 신청 방법",
    "",
    "#사주 #운세 #사주마루 #무료사주 #오늘의운세 #사주상담 #AI사주 #Shorts",
    "",
    f"⭐ {account_name} 구독하고 매일 운세 확인하세요!",
]
description = "\n".join(description_parts)[:5000]

tags = [
    "사주", "운세", "사주마루", "무료사주", "오늘의운세", "사주상담",
    "AI사주", "이번주운세", "사주보기", "사주팔자", "관상", "타로",
    account_name, "Shorts", "사주유튜브",
]

thumbnail_path = meta.get("thumbnail_youtube", "")

metadata = {
    "snippet": {
        "title": title,
        "description": description,
        "tags": tags[:15],
        "categoryId": "22",
        "defaultLanguage": "ko",
    },
    "status": {
        "privacyStatus": "public",
        "selfDeclaredMadeForKids": False,
        "madeForKids": False,
    },
}

# 4. Resumable Upload 초기화
init_res = requests.post(
    "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
    headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/mp4",
    },
    json=metadata,
)

upload_url = init_res.headers.get("Location", "")
if not upload_url:
    print("❌ YouTube 업로드 초기화 실패:", init_res.status_code, init_res.text[:300])
    exit(1)

# 5. 영상 업로드
print("  ⬆️  YouTube 업로드 중...")
with open(video_path, "rb") as f:
    video_data = f.read()

upload_res = requests.put(
    upload_url,
    headers={"Content-Type": "video/mp4"},
    data=video_data,
    timeout=300,
)

if upload_res.status_code not in (200, 201):
    print("❌ YouTube 업로드 실패:", upload_res.status_code, upload_res.text[:300])
    exit(1)

video_id = upload_res.json().get("id", "")
shorts_url = f"https://youtube.com/shorts/{video_id}" if is_shorts else f"https://youtube.com/watch?v={video_id}"
print(f"✅ YouTube 업로드 완료: {shorts_url}")

# 6. 썸네일 설정 (있는 경우)
if thumbnail_path and Path(thumbnail_path).exists():
    thumb_res = requests.post(
        f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}&uploadType=media",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "image/jpeg",
        },
        data=open(thumbnail_path, "rb").read(),
        timeout=60,
    )
    if thumb_res.status_code == 200:
        print(f"  ✅ 썸네일 설정 완료")
    else:
        print(f"  ⚠️ 썸네일 설정 실패: {thumb_res.status_code}")

meta["youtube_video_id"] = video_id
meta["youtube_url"] = shorts_url
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

print("✅ YouTube 완료")
