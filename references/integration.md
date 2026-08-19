# Meta 연결 절차 및 필수 환경변수

Instagram Reels와 Threads에 영상을 게시하려면 Meta Developer App과 장기 액세스 토큰이 필요하다.
계정마다(mom_moneytip / showpingkkultem / haru_moneytip) 별도 설정이 필요하다.

---

## 1. Meta Developer App 생성

1. https://developers.facebook.com 에 접속 → **My Apps → Create App**
2. "Business" 유형 선택
3. 다음 제품을 추가한다:
   - **Instagram Graph API** (릴스 게시)
   - **Threads API** (스레드 게시)
4. 앱을 **라이브 모드**로 전환한다 (개발 모드에서는 토큰이 60일만 유효함).

---

## 2. Instagram Graph API 설정

### 비즈니스 연결
각 Instagram 계정을 Facebook Page에 연결하고, 해당 Page를 Meta Business Suite에 등록한다.

### 필요 권한 (Scope)
```
instagram_basic
instagram_content_publish
pages_show_list
pages_read_engagement
```

### 액세스 토큰 발급 절차
```bash
# 1) 단기 사용자 토큰 (Facebook OAuth 로그인)
#    Graph API Explorer (https://developers.facebook.com/tools/explorer/) 에서
#    위 4가지 scope를 선택해 단기 토큰을 발급한다.

# 2) 장기 토큰으로 교환 (60일 → 장기)
curl "https://graph.facebook.com/v21.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id=<APP_ID>
  &client_secret=<APP_SECRET>
  &fb_exchange_token=<단기_토큰>"

# 3) 영구 페이지 토큰 발급
#    /me/accounts 로 연결된 페이지 목록을 조회한 뒤,
#    대상 페이지의 access_token 을 가져온다.

# 4) Instagram User ID 확인
curl "https://graph.facebook.com/v21.0/<PAGE_ID>?fields=instagram_business_account&access_token=<PAGE_TOKEN>"
# 반환된 instagram_business_account.id 가 META_<ACCOUNT>_IG_USER_ID 값이다.
```

### 업로드 가능 동영상 규격
- 포맷: MP4 (H.264 비디오, AAC 오디오)
- 해상도: 1080×1920 (9:16)
- 길이: 3초 이상 ~ 90초 이하 (릴스)
- 파일 크기: 1 GB 이하
- 반드시 **공개 HTTPS URL**에서 서빙되어야 한다.

---

## 3. Threads API 설정

### 필요 권한 (Scope)
```
threads_basic
threads_content_publish
```

### 액세스 토큰 발급 절차
```bash
# 1) 인증 URL로 사용자 로그인 (Threads 앱 대시보드에서 생성)
https://threads.net/oauth/authorize
  ?client_id=<APP_ID>
  &redirect_uri=<REDIRECT_URI>
  &scope=threads_basic,threads_content_publish
  &response_type=code

# 2) 단기 토큰 교환
curl -X POST https://graph.threads.net/oauth/access_token \
  -F client_id=<APP_ID> \
  -F client_secret=<APP_SECRET> \
  -F code=<CODE> \
  -F grant_type=authorization_code \
  -F redirect_uri=<REDIRECT_URI>

# 3) 장기 토큰 교환 (60일)
curl "https://graph.threads.net/access_token
  ?grant_type=th_exchange_token
  &client_secret=<APP_SECRET>
  &access_token=<단기_토큰>"

# 4) Threads User ID 확인
curl "https://graph.threads.net/v1.0/me?fields=id&access_token=<THREADS_LONG_TOKEN>"
```

---

## 4. 동영상 공개 HTTPS 저장소

Meta API는 서버가 직접 URL을 가져가므로 영상 파일이 공개 HTTPS URL에서 서빙되어야 한다.

### 옵션 A: AWS S3 공개 버킷
```bash
# 버킷 생성 후 퍼블릭 액세스 허용
# 업로드 후 https://<bucket>.s3.<region>.amazonaws.com/<key> 형태의 URL 사용
```

### 옵션 B: 기타 CDN / 오브젝트 스토리지
- Cloudflare R2, Google Cloud Storage, Backblaze B2 등
- 공개 읽기 권한과 HTTPS 지원 필수

`META_VIDEO_BUCKET_URL` 환경변수에 **파일 이름을 붙이면 완성되는 URL 접두사**를 설정한다.
예: `https://my-bucket.s3.ap-northeast-2.amazonaws.com/shorts/`

---

## 5. Naver Clova Voice TTS

한국어 TTS 음성을 생성하려면 Naver Cloud 콘솔에서 Clova Voice API 키를 발급한다.
- https://www.ncloud.com/product/aiService/clovaVoice
- API Gateway → "Clova Voice" 서비스 이용 신청
- 발급된 X-NCP-APIGW-API-KEY-ID, X-NCP-APIGW-API-KEY 를 환경변수에 설정한다.

---

## 6. FFmpeg 설치 확인

동영상 렌더링에 `ffmpeg`이 필요하다.

```bash
ffmpeg -version  # 4.x 이상이면 정상
```

컨테이너 환경에서는 보통 이미 설치돼 있다.

---

## 7. 필수 환경변수 목록

`.env` 파일에 다음 변수를 채운다. 토큰은 절대 Git에 커밋하지 않는다.

```dotenv
# ── Meta Developer App ─────────────────────────────────────────────────────
META_APP_ID=
META_APP_SECRET=
META_API_VERSION=v21.0
META_API_MODE=mock           # mock | live

# ── 계정 1: mom_moneytip ──────────────────────────────────────────────────
META_MOM_MONEYTIP_IG_USER_ID=
META_MOM_MONEYTIP_THREADS_USER_ID=
META_MOM_MONEYTIP_ACCESS_TOKEN=

# ── 계정 2: showpingkkultem ───────────────────────────────────────────────
META_SHOWPINGKKULTEM_IG_USER_ID=
META_SHOWPINGKKULTEM_THREADS_USER_ID=
META_SHOWPINGKKULTEM_ACCESS_TOKEN=

# ── 계정 3: haru_moneytip ─────────────────────────────────────────────────
META_HARU_MONEYTIP_IG_USER_ID=
META_HARU_MONEYTIP_THREADS_USER_ID=
META_HARU_MONEYTIP_ACCESS_TOKEN=

# ── 영상 공개 저장소 ───────────────────────────────────────────────────────
META_VIDEO_BUCKET_URL=       # 예: https://my-bucket.s3.ap-northeast-2.amazonaws.com/shorts/

# ── TTS (Naver Clova Voice) ────────────────────────────────────────────────
NAVER_TTS_CLIENT_ID=
NAVER_TTS_CLIENT_SECRET=
NAVER_TTS_SPEAKER=nara      # nara | mijin | jinho | etc.

# ── 콘텐츠 출력 경로 ───────────────────────────────────────────────────────
CONTENT_OUTPUT_DIR=data/content
```

---

## 8. 토큰 갱신 주기

| 토큰 종류 | 유효 기간 | 갱신 방법 |
|---|---|---|
| Instagram 장기 토큰 | 60일 | `/oauth/access_token?grant_type=fb_exchange_token` |
| Instagram 페이지 토큰 | 만료 없음 | 페이지 역할 유지 시 지속 |
| Threads 장기 토큰 | 60일 | `/access_token?grant_type=th_refresh_token` |

60일 전에 `cron` 혹은 자동화 스크립트로 갱신한다:
```bash
python -m shopping_shorts_sync meta refresh-tokens
```

---

## 9. 계정 연결 검증

```bash
# 환경변수 설정 후 연결 상태 확인
python -m shopping_shorts_sync meta verify-accounts

# 출력 예시
[OK] mom_moneytip      instagram  user_id=123… token_expires=2025-10-01
[OK] mom_moneytip      threads    user_id=456… token_expires=2025-10-01
[OK] showpingkkultem   instagram  user_id=789…
...
```
