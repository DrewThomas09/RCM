"""Shared test hardening hooks.

Python 3.14 surfaces unclosed ``urllib`` error responses as
``ResourceWarning`` during object finalization. A large portion of this
suite intentionally asserts 4xx/5xx paths via ``HTTPError``; under
``PYTHONWARNINGS=error`` those otherwise-benign leaked handles turn into
test failures unrelated to product behavior.

We close caught ``HTTPError`` instances centrally so strict warning runs
exercise the app, not urllib response cleanup.
"""
from __future__ import annotations

from urllib.error import HTTPError


def _close_http_error(exc: BaseException | None) -> None:
    if isinstance(exc, HTTPError):
        try:
            exc.close()
        except OSError:
            # ``HTTPError`` wraps a file-like object that may already be
            # closed by the time cleanup runs.
            pass


if not getattr(HTTPError, "_rcm_autoclose", False):
    def _http_error_del(self):
        _close_http_error(self)

    HTTPError.__del__ = _http_error_del
    HTTPError._rcm_autoclose = True
