"""
유튜브 쇼츠 자동 업로드
필요: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN
"""
import os, json, requests

CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    print("⚠️  YouTube API 미설정 — 건너뜀")
    exit(0)

with open("scripts/sns_output/meta.json", encoding="utf-8") as f:
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

# 2. 이미지를 동영상으로 변환 (ffmpeg: 정지 이미지 → 15초 쇼츠)
import subprocess
image_path = meta["image_path"]
video_path = image_path.replace(".jpg", "_shorts.mp4")

result = subprocess.run([
    "ffmpeg", "-y", "-loop", "1", "-i", image_path,
    "-c:v", "libx264", "-t", "15", "-pix_fmt", "yuv420p",
    "-vf", "scale=1080:1920",
    video_path
], capture_output=True, text=True)

if result.returncode != 0:
    print("❌ ffmpeg 변환 실패:", result.stderr[-500:])
    exit(1)

print(f"✅ 영상 생성: {video_path}")

# 3. YouTube 업로드 (resumable upload)
title = content.get("youtube_title", f"이번 주 사주 운세 {meta['date']}")[:100]
description = content.get("youtube_description", content.get("main_text", ""))
tags = ["사주", "운세", "사주마루", "AI사주", "이번주운세", "Shorts"]

metadata = {
    "snippet": {
        "title": title,
        "description": description + "\n\n사주마루 AI: https://saju-maru.com",
        "tags": tags,
        "categoryId": "22",  # People & Blogs
        "defaultLanguage": "ko",
    },
    "status": {
        "privacyStatus": "public",
        "selfDeclaredMadeForKids": False,
    }
}

# Resumable upload 초기화
init_res = requests.post(
    "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
    headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/mp4",
    },
    json=metadata
)

upload_url = init_res.headers.get("Location", "")
if not upload_url:
    print("❌ YouTube 업로드 초기화 실패:", init_res.status_code, init_res.text[:300])
    exit(1)

# 파일 업로드
with open(video_path, "rb") as f:
    video_data = f.read()

upload_res = requests.put(
    upload_url,
    headers={"Content-Type": "video/mp4"},
    data=video_data,
    timeout=120
)

if upload_res.status_code in (200, 201):
    video_id = upload_res.json().get("id", "")
    print(f"✅ YouTube 업로드 완료: https://youtube.com/shorts/{video_id}")
    meta["youtube_video_id"] = video_id
    with open("scripts/sns_output/meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
else:
    print("❌ YouTube 업로드 실패:", upload_res.status_code, upload_res.text[:300])
    exit(1)
