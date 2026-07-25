from __future__ import annotations

import os

from .models import PublishResult

_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
_CHUNK_SIZE = 1024 * 1024  # 1 MiB


class YouTubePublisher:
    """Upload a short video to YouTube via the Data API v3 (OAuth2)."""

    def __init__(
        self,
        client_secrets_file: str,
        token_file: str = "data/youtube_token.json",
        dry_run: bool = False,
    ) -> None:
        self.client_secrets_file = client_secrets_file
        self.token_file = token_file
        self.dry_run = dry_run

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_credentials(self):
        """Return valid OAuth2 credentials, refreshing / re-running the flow as needed."""
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request

        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, _SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_file, _SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Persist the refreshed / new token for next time.
            token_dir = os.path.dirname(self.token_file)
            if token_dir:
                os.makedirs(token_dir, exist_ok=True)
            with open(self.token_file, "w") as fh:
                fh.write(creds.to_json())

        return creds

    def _build_service(self):
        from googleapiclient.discovery import build

        creds = self._get_credentials()
        return build("youtube", "v3", credentials=creds)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def publish(self, video_path: str, caption: str, product_name: str) -> PublishResult:
        """Upload *video_path* as a YouTube Short and return a :class:`PublishResult`.

        Parameters
        ----------
        video_path:
            Absolute or relative path to the ``.mp4`` file.
        caption:
            Long-form description / caption used as the video description.
        product_name:
            Displayed as the video title (truncated to 100 characters).
        """
        if self.dry_run:
            return PublishResult(
                platform="youtube",
                success=True,
                post_url="https://www.youtube.com/watch?v=DRY_RUN_ID",
                post_id="DRY_RUN_ID",
            )

        from googleapiclient.http import MediaFileUpload

        body = {
            "snippet": {
                "title": product_name[:100],
                "description": caption,
                "tags": ["쿠팡", "쇼핑", "숏츠"],
                "categoryId": "26",
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/*",
            resumable=True,
            chunksize=_CHUNK_SIZE,
        )

        try:
            service = self._build_service()
            request = service.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media,
            )

            response = None
            while response is None:
                _status, response = request.next_chunk()

            video_id = response.get("id", "")
            post_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else None
            return PublishResult(
                platform="youtube",
                success=True,
                post_url=post_url,
                post_id=video_id or None,
            )
        except Exception as exc:  # noqa: BLE001
            return PublishResult(
                platform="youtube",
                success=False,
                error=str(exc),
            )
