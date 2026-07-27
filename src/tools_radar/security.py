"""Input and output safety helpers for the public tools catalog."""

from __future__ import annotations

import html
import ipaddress
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from ..url_security import UnsafeURLError, safe_request

_TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "referrer",
    "source",
}
_SECRET_PATTERNS = (
    re.compile(r"\b(?:sk|gsk|xai|hf)_[A-Za-z0-9_-]{16,}\b", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b", re.IGNORECASE),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b", re.IGNORECASE),
    re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)"
        r"\s*[:=]\s*['\"]?[^\s'\"&]{8,}"
    ),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}"),
)


def sanitize_text(value: object, *, max_length: int = 600) -> str:
    """Turn untrusted feed or API text into bounded plain text."""
    if value is None:
        return ""
    raw = html.unescape(str(value))
    plain = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    for pattern in _SECRET_PATTERNS:
        plain = pattern.sub("[已移除敏感信息]", plain)
    plain = "".join(
        char for char in plain if char in "\n\t" or ord(char) >= 32
    )
    plain = re.sub(r"\s+", " ", plain).strip()
    if len(plain) <= max_length:
        return plain
    return plain[: max(0, max_length - 1)].rstrip() + "…"


def _reject_private_literal(hostname: str) -> None:
    try:
        address = ipaddress.ip_address(hostname.split("%", 1)[0])
    except ValueError:
        return
    if not address.is_global:
        raise UnsafeURLError("URL host must be globally routable")


def sanitize_public_url(
    value: object,
    *,
    allowed_hosts: set[str] | None = None,
) -> str:
    """Validate a public output URL without performing a DNS request."""
    raw = str(value or "").strip()
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise UnsafeURLError(f"Invalid URL: {exc}") from exc
    if parsed.scheme.lower() != "https":
        raise UnsafeURLError("Public catalog URLs must use https")
    if not parsed.hostname:
        raise UnsafeURLError("URL has no hostname")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeURLError("URL must not contain embedded credentials")
    if port not in {None, 443}:
        raise UnsafeURLError("Public catalog URLs must use the default HTTPS port")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise UnsafeURLError("localhost destinations are not allowed")
    _reject_private_literal(hostname)
    if allowed_hosts and not any(
        hostname == allowed or hostname.endswith(f".{allowed}")
        for allowed in allowed_hosts
    ):
        raise UnsafeURLError(f"URL host is not allowed: {hostname}")

    query = [
        (name, value)
        for name, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not name.lower().startswith("utm_")
        and name.lower() not in _TRACKING_PARAMS
    ]
    return urlunsplit(
        (
            "https",
            hostname,
            parsed.path or "/",
            urlencode(query, doseq=True),
            "",
        )
    )


def safe_install_command(value: object, *, max_length: int = 500) -> str:
    """Keep an installation command as inert, redacted display text."""
    command = sanitize_text(value, max_length=max_length)
    for pattern in _SECRET_PATTERNS:
        command = pattern.sub("[REDACTED]", command)
    return command


def is_safe_url(value: object, *, allowed_hosts: set[str] | None = None) -> bool:
    try:
        sanitize_public_url(value, allowed_hosts=allowed_hosts)
    except UnsafeURLError:
        return False
    return True


__all__ = [
    "UnsafeURLError",
    "is_safe_url",
    "safe_install_command",
    "safe_request",
    "sanitize_public_url",
    "sanitize_text",
]
