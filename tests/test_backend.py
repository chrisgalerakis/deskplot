from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import pandas as pd

import deskplot
from deskplot import ChartFigure
from deskplot.backend import (
    HTML2CANVAS_JS,
    _create_chart_html,
    _create_table_html,
    _hex_to_rgba,
)


def _fig():
    fig = ChartFigure()
    fig.add_scatter(y=[1, 2, 3])
    return fig


def test_hex_to_rgba():
    assert _hex_to_rgba("#00ACFF", 0.2) == "rgba(0, 172, 255, 0.2)"
    assert _hex_to_rgba("5b9aff", 0.5) == "rgba(91, 154, 255, 0.5)"
    # Malformed input falls back to the default accent
    assert _hex_to_rgba("blue", 0.2) == "rgba(91, 154, 255, 0.2)"


def test_html2canvas_is_vendored():
    assert len(HTML2CANVAS_JS) > 100_000
    assert "html2canvas" in HTML2CANVAS_JS


def test_chart_html_contains_brand_and_title():
    html = _create_chart_html(_fig(), title="My Chart")
    assert "deskplot" in html
    assert "My Chart" in html


def test_chart_html_has_no_external_script_tags():
    html = _create_chart_html(_fig(), title="T")
    assert '<script src="http' not in html
    assert "cdnjs.cloudflare.com" not in html


def test_chart_html_secondary_brand_hidden_by_default():
    html = _create_chart_html(_fig(), title="T")
    # The separator pipe span only renders when brand_secondary is set
    assert 'text-shadow: none;">|</span>' not in html


def test_chart_html_respects_configure():
    deskplot.configure(brand="ACME", brand_secondary="DESK", color_primary="#00C853")
    html = _create_chart_html(_fig(), title="T")
    assert "ACME" in html
    assert "DESK" in html
    assert "#00C853" in html


def test_table_html_renders_data():
    df = pd.DataFrame({"Asset": ["ES", "NQ"], "Pos": [1.5, -0.5]})
    html = _create_table_html(df, title="Tbl")
    assert "Asset" in html
    assert "ES" in html
    assert "Tbl" in html


def test_table_html_source_footer_only_when_set():
    df = pd.DataFrame({"A": [1]})
    html_without = _create_table_html(df, title="T")
    assert "Source:" not in html_without
    html_with = _create_table_html(df, title="T", source="Vendor")
    assert "Source: Vendor" in html_with


def test_browser_fallback_writes_html(monkeypatch):
    opened = {}
    monkeypatch.setattr(
        "deskplot.backend.webbrowser.open", lambda url: opened.setdefault("url", url)
    )
    _fig().show(title="Fallback", external=True)
    assert opened["url"].startswith("file://")
    # url2pathname handles Windows URIs (file:///C:/...) correctly;
    # naive prefix-stripping does not
    path = Path(url2pathname(urlparse(opened["url"]).path))
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "plotly-chart" in content
    assert "Fallback" in content
    path.unlink()


def test_table_html_title_with_quote_is_js_safe():
    df = pd.DataFrame({"A": [1]})
    html = _create_table_html(df, title="O'Brien Desk")
    # The CSV download filename must be JSON-encoded so the apostrophe
    # cannot terminate the JS string literal
    assert 'a.download = "O\'Brien_Desk.csv";' in html


def test_table_html_escapes_script_terminator_in_cells():
    df = pd.DataFrame({"A": ["</script><b>x</b>"]})
    html = _create_table_html(df, title="T")
    assert "<\\/script>" in html


def test_table_html_uses_default_brand():
    df = pd.DataFrame({"A": [1]})
    table = _create_table_html(df)
    assert '<div class="logo-text">deskplot</div>' in table
