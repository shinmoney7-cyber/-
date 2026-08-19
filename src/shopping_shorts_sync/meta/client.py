from __future__ import annotations

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30


class MetaApiError(Exception):
    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


class MetaApiClient:
    """Thin wrapper around the Meta Graph API. One instance per access token."""

    GRAPH_BASE = "https://graph.facebook.com"
    THREADS_BASE = "https://graph.threads.net"

    def __init__(self, access_token: str, api_version: str = "v21.0"):
        self.access_token = access_token
        self.api_version = api_version
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "shopping-shorts-sync/1.0"

    def _graph_url(self, path: str) -> str:
        return f"{self.GRAPH_BASE}/{self.api_version}/{path.lstrip('/')}"

    def _threads_url(self, path: str) -> str:
        return f"{self.THREADS_BASE}/{self.api_version}/{path.lstrip('/')}"

    def _raise_if_error(self, resp: requests.Response) -> dict:
        try:
            data = resp.json()
        except ValueError as e:
            raise MetaApiError(f"non-JSON response {resp.status_code}: {resp.text[:200]}") from e

        if "error" in data:
            err = data["error"]
            raise MetaApiError(err.get("message", str(err)), code=err.get("code"))

        if not resp.ok:
            raise MetaApiError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        return data

    def graph_get(self, path: str, **params: Any) -> dict:
        params["access_token"] = self.access_token
        resp = self._session.get(self._graph_url(path), params=params, timeout=_DEFAULT_TIMEOUT)
        return self._raise_if_error(resp)

    def graph_post(self, path: str, **data: Any) -> dict:
        data["access_token"] = self.access_token
        resp = self._session.post(self._graph_url(path), data=data, timeout=_DEFAULT_TIMEOUT)
        return self._raise_if_error(resp)

    def threads_get(self, path: str, **params: Any) -> dict:
        params["access_token"] = self.access_token
        resp = self._session.get(self._threads_url(path), params=params, timeout=_DEFAULT_TIMEOUT)
        return self._raise_if_error(resp)

    def threads_post(self, path: str, **data: Any) -> dict:
        data["access_token"] = self.access_token
        resp = self._session.post(self._threads_url(path), data=data, timeout=_DEFAULT_TIMEOUT)
        return self._raise_if_error(resp)

    def poll_until_ready(
        self,
        poll_fn,
        ready_statuses: set[str],
        error_statuses: set[str],
        *,
        max_attempts: int = 20,
        interval: float = 5.0,
        label: str = "container",
    ) -> str:
        """Polls poll_fn() until it returns a status in ready_statuses.

        Returns the final status string. Raises MetaApiError on error status or timeout.
        """
        for attempt in range(max_attempts):
            status = poll_fn()
            logger.debug("%s status [%d/%d]: %s", label, attempt + 1, max_attempts, status)
            if status in ready_statuses:
                return status
            if status in error_statuses:
                raise MetaApiError(f"{label} entered error state: {status}")
            if attempt < max_attempts - 1:
                time.sleep(interval)
        raise MetaApiError(f"{label} not ready after {max_attempts} attempts (last status: {status})")
