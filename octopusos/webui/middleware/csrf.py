"""CSRF protection middleware (minimal implementation for tests)."""

from __future__ import annotations

import logging
import os
import secrets
from typing import Callable, Optional
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

CSRF_TOKEN_LENGTH = 32
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_SESSION_KEY = "_csrf_token"

PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

EXPECTED_GENERAL_EXEMPTIONS = {
    "/health",
    "/api/health",
    "/static/",
    "/ws/",
    "/webhook/",
}

EXPECTED_API_WHITELIST = {
    "/api/health",
    "/api/csrf-token",
}


def validate_exemption_contract(
    configured_exemptions: list[str],
    configured_api_whitelist: list[str],
) -> None:
    configured_general = set(configured_exemptions)
    configured_api = set(configured_api_whitelist)

    unexpected_general = configured_general - EXPECTED_GENERAL_EXEMPTIONS
    unexpected_api = configured_api - EXPECTED_API_WHITELIST

    if unexpected_general:
        raise AssertionError(
            "SECURITY CONTRACT VIOLATION: Unexpected CSRF exemptions detected!\n"
            f"Unauthorized exemptions: {unexpected_general}"
        )

    if unexpected_api:
        raise AssertionError(
            "SECURITY CONTRACT VIOLATION: Unexpected API whitelist entries detected!\n"
            f"Unauthorized whitelist entries: {unexpected_api}"
        )

    missing_general = EXPECTED_GENERAL_EXEMPTIONS - configured_general
    missing_api = EXPECTED_API_WHITELIST - configured_api

    if missing_general:
        logger.warning(
            "CSRF Exemption Contract: Some expected exemptions are not configured: %s",
            missing_general,
        )
    if missing_api:
        logger.warning(
            "CSRF Exemption Contract: Some expected API whitelist entries are not configured: %s",
            missing_api,
        )


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """Minimal CSRF middleware with origin check and token validation."""

    def __init__(
        self,
        app: FastAPI,
        exempt_paths: Optional[list[str]] = None,
        token_header: str = CSRF_HEADER_NAME,
        cookie_name: str = CSRF_COOKIE_NAME,
        enforce_for_api: bool = True,
        check_origin: bool = True,
        validate_contract: bool = True,
    ):
        super().__init__(app)
        self.exempt_paths = exempt_paths or [
            "/health",
            "/api/health",
            "/static/",
            "/ws/",
            "/webhook/",
        ]
        self.api_whitelist = [
            "/api/health",
            "/api/csrf-token",
        ]
        self.token_header = token_header
        self.cookie_name = cookie_name
        self.enforce_for_api = enforce_for_api
        self.check_origin = check_origin

        if validate_contract:
            validate_exemption_contract(self.exempt_paths, self.api_whitelist)

    def _is_exempt(self, path: str) -> bool:
        if any(path.startswith(exempt) for exempt in self.exempt_paths):
            return True
        if any(path.startswith(api) for api in self.api_whitelist):
            return True
        return False

    def _generate_token(self) -> str:
        return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)

    def _check_origin(self, request: Request) -> bool:
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        host = request.headers.get("host")
        scheme = request.url.scheme

        if not host:
            return False

        if origin:
            try:
                origin_host = urlparse(origin).netloc or origin
            except Exception:
                origin_host = origin
            return origin_host == host

        if referer:
            try:
                parsed = urlparse(referer)
                return parsed.netloc == host and parsed.scheme == scheme
            except Exception:
                return False

        return False

    async def dispatch(self, request: Request, call_next: Callable):
        if request.method in SAFE_METHODS or self._is_exempt(request.url.path):
            return await call_next(request)

        if self.check_origin and not self._check_origin(request):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": {
                        "code": "ORIGIN_CHECK_FAILED",
                        "message": "Origin/Referer validation failed",
                    }
                },
            )

        cookie_token = request.cookies.get(self.cookie_name)
        header_token = request.headers.get(self.token_header)

        if cookie_token and header_token and cookie_token == header_token:
            return await call_next(request)

        return JSONResponse(
            status_code=403,
            content={
                "detail": {
                    "code": "CSRF_TOKEN_INVALID",
                    "message": "Missing or invalid CSRF token",
                }
            },
        )


__all__ = [
    "CSRFProtectionMiddleware",
    "EXPECTED_GENERAL_EXEMPTIONS",
    "EXPECTED_API_WHITELIST",
    "validate_exemption_contract",
]
