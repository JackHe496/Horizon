from pathlib import Path


DOCS = Path("docs")


def test_radar_pages_are_static_and_have_expected_routes():
    expected = {
        "index.html": "data-radar-mode=\"home\"",
        "tools.html": "data-radar-mode=\"directory\"",
        "tool-stream.html": "data-radar-mode=\"daily\"",
        "weekly.html": "data-radar-mode=\"weekly\"",
        "favorites.html": "data-radar-mode=\"favorites\"",
    }
    for filename, marker in expected.items():
        text = (DOCS / filename).read_text()
        assert marker in text
        assert "<form" not in text


def test_legacy_markdown_homepage_is_redirected_away_from_site_root():
    tombstone = (DOCS / "index.md").read_text()

    assert "Compatibility tombstone" in tombstone
    assert tombstone.lstrip().startswith("---")
    assert "permalink: /legacy-home-tombstone/" in tombstone


def test_browser_renderer_never_injects_source_html():
    renderer = (DOCS / "assets/js/tools-radar.js").read_text()
    assert ".innerHTML" not in renderer
    assert "document.createElement" in renderer
    assert "localStorage" in renderer
    assert "navigator.clipboard.writeText" in renderer


def test_layout_enforces_content_security_policy_and_no_telemetry():
    layout = (DOCS / "_layouts/default.html").read_text()
    assert "Content-Security-Policy" in layout
    assert "script-src 'self'" in layout
    assert "connect-src 'self'" in layout
    assert "analytics" not in layout.casefold()
