"""REST client for the Mintlayer indexer (mirrors go-sdk/indexer).

All paths are relative to the ``/api/v2`` base appended to the configured URL.
Errors: any HTTP status >= 400 raises :class:`HTTPError` with the response
body; transport/decode failures raise :class:`IndexerError`.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests

__all__ = ["HTTPError", "IndexerError", "IndexerHTTP"]


class IndexerError(Exception):
    """Transport or codec failure."""


class HTTPError(Exception):
    """Non-2xx HTTP response from the indexer."""

    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"HTTP {status_code}: {body}")
        self.status_code = status_code
        self.body = body


def _seg(value: Any) -> str:
    """URL-encode a path segment (defense against path traversal/injection)."""
    return quote(str(value), safe="")


class IndexerHTTP:
    """HTTP layer for the indexer client (GET + one text/plain POST route)."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        self.api_base = base_url.rstrip("/") + "/api/v2"
        self.timeout = timeout
        self._owns_session = session is None
        self._session = session if session is not None else requests.Session()

    def get(self, path: str, query: dict[str, Any] | None = None) -> Any:
        """GET ``path`` and return the decoded JSON body."""
        url = self.api_base + path
        try:
            resp = self._session.get(
                url,
                params=query or None,
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            )
        except requests.RequestException as exc:
            raise IndexerError(f"http request: {exc}") from exc
        return self._decode(path, resp)

    def post_text(self, path: str, body: str) -> Any:
        """POST ``body`` verbatim as ``text/plain`` and return decoded JSON."""
        url = self.api_base + path
        try:
            resp = self._session.post(
                url,
                data=body,
                timeout=self.timeout,
                headers={"Content-Type": "text/plain", "Accept": "application/json"},
            )
        except requests.RequestException as exc:
            raise IndexerError(f"http request: {exc}") from exc
        return self._decode(path, resp)

    def _decode(self, path: str, resp: requests.Response) -> Any:
        if resp.status_code >= 400:
            raise HTTPError(resp.status_code, resp.text.strip())
        try:
            return resp.json()
        except ValueError as exc:
            raise IndexerError(f"decode response for {path}: {exc}") from exc

    def close(self) -> None:
        """Close the HTTP session (only if the client created it)."""
        if self._owns_session:
            self._session.close()
