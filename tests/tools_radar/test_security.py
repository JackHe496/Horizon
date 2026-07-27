from __future__ import annotations

import pytest

from src.tools_radar.security import (
    UnsafeURLError,
    safe_install_command,
    sanitize_public_url,
    sanitize_text,
)


def test_untrusted_html_is_reduced_to_plain_text_and_secrets_are_removed():
    value = sanitize_text(
        '<img src=x onerror="alert(1)">Useful <script>alert(2)</script> '
        "api_key=super-secret-value"
    )

    assert "<" not in value
    assert "onerror" not in value
    assert "super-secret-value" not in value
    assert "Useful" in value


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "http://example.com/tool",
        "https://user:secret@example.com/tool",
        "https://127.0.0.1/tool",
        "https://10.0.0.1/tool",
        "https://localhost/tool",
    ],
)
def test_public_catalog_rejects_unsafe_urls(url):
    with pytest.raises(UnsafeURLError):
        sanitize_public_url(url)


def test_url_tracking_is_removed_but_original_path_is_preserved():
    result = sanitize_public_url(
        "https://example.com/tool?utm_source=rss&version=2#install"
    )
    assert result == "https://example.com/tool?version=2"


def test_install_commands_are_inert_redacted_text():
    command = safe_install_command(
        '<b>tool --token ghp_abcdefghijklmnopqrstuvwxyz012345</b>'
    )
    assert "<b>" not in command
    assert "ghp_" not in command
    assert "[已移除敏感信息]" in command
