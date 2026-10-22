# GitHub Secrets 설정 가이드

GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret

## 공통 시크릿 (한 번만)

| Secret 이름 | 설명 | 발급처 |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude AI API 키 | https://console.anthropic.com |
| `GMAIL_APP_PASSWORD` | Gmail 앱 비밀번호 | Google 계정 → 보안 → 앱 비밀번호 |
| `TYPEFULLY_API_KEY` | Typefully API 키 | https://typefully.com → Settings → API |

---

## 계정별 시크릿 (SM=사주마루 / UN=사주보는언니 / S77=사주마루77)

각 `XX_` prefix를 SM, UN, S77로 교체해서 3세트 등록

### Meta (Instagram / Facebook / Threads)
> Meta Business Suite → https://developers.facebook.com

| Secret | 발급 방법 |
|---|---|
| `XX_INSTAGRAM_ACCESS_TOKEN` | Graph API → Instagram Basic Display → Long-lived token |
| `XX_INSTAGRAM_USER_ID` | `GET /me?fields=id` 로 확인 |
| `XX_FACEBOOK_PAGE_ID` | 페이지 URL 또는 About에서 확인 |
| `XX_FACEBOOK_PAGE_ACCESS_TOKEN` | Graph API Explorer → Page token |
| `XX_THREADS_ACCESS_TOKEN` | Meta Developer → Threads API |
| `XX_THREADS_USER_ID` | Threads API `/me` 엔드포인트 |

### Twitter/X
> https://developer.twitter.com → Projects & Apps → Keys and Tokens

| Secret | 설명 |
|---|---|
| `XX_TWITTER_API_KEY` | API Key (Consumer Key) |
| `XX_TWITTER_API_SECRET` | API Secret (Consumer Secret) |
| `XX_TWITTER_ACCESS_TOKEN` | Access Token |
| `XX_TWITTER_ACCESS_TOKEN_SECRET` | Access Token Secret |

※ Free tier: 월 1500 트윗 (2시간 간격 9회 × 3계정 × 30일 = 810회 → 여유 있음)

### TikTok
> https://developers.tiktok.com → Manage Apps → Content Posting API 신청

| Secret | 설명 |
|---|---|
| `XX_TIKTOK_CLIENT_KEY` | Client Key |
| `XX_TIKTOK_CLIENT_SECRET` | Client Secret |
| `XX_TIKTOK_REFRESH_TOKEN` | OAuth Refresh Token |

※ Content Posting API는 비즈니스 계정 + 사전 심사 필요 (1-2주)

### YouTube
> Google Cloud Console → 프로젝트 → YouTube Data API v3 → OAuth 2.0

| Secret | 설명 |
|---|---|
| `XX_YOUTUBE_CLIENT_ID` | OAuth 2.0 Client ID |
| `XX_YOUTUBE_CLIENT_SECRET` | OAuth 2.0 Client Secret |
| `XX_YOUTUBE_REFRESH_TOKEN` | `python scripts/get_youtube_token.py` 실행 후 발급 |

※ 무료 할당: 10,000 units/일 (영상 업로드 1600 units → 최대 6회/일)

### Naver (사주마루, 사주보는언니만 해당)
> https://developers.naver.com → Application 등록 → 블로그 글쓰기 권한

| Secret | 설명 |
|---|---|
| `XX_NAVER_CLIENT_ID` | 앱 Client ID |
| `XX_NAVER_CLIENT_SECRET` | 앱 Client Secret |
| `XX_NAVER_ACCESS_TOKEN` | OAuth access token |
| `XX_NAVER_REFRESH_TOKEN` | OAuth refresh token |
| `XX_NAVER_ID` | 네이버 로그인 ID (지식인용) |
| `XX_NAVER_PW` | 네이버 비밀번호 (지식인용) |

---

## 우선 등록 추천 순서 (수익 기준)

1. **`ANTHROPIC_API_KEY`** ← 이게 없으면 콘텐츠 생성 안 됨 (필수)
2. **`GMAIL_APP_PASSWORD`** ← 결과 알림용 (권장)
3. **Meta tokens** (Instagram/Threads/Facebook) ← 팔로워 있음
4. **Twitter/X** ← 빠른 발급, 무료 플랜 가능
5. **TikTok** ← 심사 필요, 미리 신청
6. **YouTube** ← 영상 자동화는 추후
7. **Naver** ← 블로그/지식인

---

## 수동 테스트 방법

GitHub Actions → auto_post_2h → Run workflow
- account_id: `sm` (사주마루만)
- hour_kst: `06` (아침 운세 테스트)
