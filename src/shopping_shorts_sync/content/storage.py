from __future__ import annotations

import abc
import logging
import os
import urllib.parse

import requests

logger = logging.getLogger(__name__)


class VideoStorage(abc.ABC):
    @abc.abstractmethod
    def upload(self, local_path: str, filename: str) -> str:
        """Upload file and return the public HTTPS URL."""


class HttpPutStorage(VideoStorage):
    """Uploads via HTTP PUT to a pre-signed URL or a simple static server.

    Set META_VIDEO_BUCKET_URL to a base URL; the filename is appended.
    Example: META_VIDEO_BUCKET_URL=https://cdn.example.com/shorts/
    → uploads to https://cdn.example.com/shorts/<filename>
    """

    def __init__(self, bucket_url: str):
        if not bucket_url.endswith("/"):
            bucket_url += "/"
        self._bucket_url = bucket_url

    def upload(self, local_path: str, filename: str) -> str:
        target_url = urllib.parse.urljoin(self._bucket_url, filename)
        with open(local_path, "rb") as f:
            resp = requests.put(target_url, data=f, timeout=120)
        if not resp.ok:
            raise RuntimeError(f"upload failed [{resp.status_code}]: {target_url}")
        logger.info("uploaded: %s -> %s", local_path, target_url)
        return target_url


class MockStorage(VideoStorage):
    """Returns a fake public URL without uploading anything."""

    BASE = "https://mock-cdn.example.com/shorts/"

    def upload(self, local_path: str, filename: str) -> str:
        url = self._base + filename
        logger.info("mock upload: %s -> %s", local_path, url)
        return url

    @property
    def _base(self) -> str:
        return self.BASE
