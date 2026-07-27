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


def test_color_brand_decouples_wordmark_from_buttons():
    deskplot.configure(color_brand="#ffffff", color_primary="#123456")
    html = _create_chart_html(_fig(), title="T")
    # White wordmark, blue-ish buttons — previously impossible
    assert 'color: #ffffff;">deskplot</span>' in html
    assert "background: #123456" in html


def test_color_brand_defaults_to_color_primary():
    html = _create_chart_html(_fig(), title="T")
    assert 'color: #5b9aff;">deskplot</span>' in html


def test_table_logo_uses_color_brand():
    deskplot.configure(color_brand="#ffffff")
    html = _create_table_html(pd.DataFrame({"A": [1]}), title="T")
    logo_css = html.split(".logo-text {")[1].split("}")[0]
    assert "color: #ffffff;" in logo_css


def test_header_timestamp_shown_by_default():
    html = _create_chart_html(_fig(), title="T")
    assert 'id="timestamp-text"' in html
    table = _create_table_html(pd.DataFrame({"A": [1]}), title="T")
    assert '<div class="timestamp">' in table


def test_header_timestamp_can_be_hidden():
    deskplot.configure(show_header_timestamp=False)
    html = _create_chart_html(_fig(), title="T")
    assert 'id="timestamp-text"' not in html
    table = _create_table_html(pd.DataFrame({"A": [1]}), title="T")
    assert '<div class="timestamp">' not in table


def test_chart_chrome_follows_color_accent():
    deskplot.configure(color_accent="#ff8800")
    html = _create_chart_html(_fig(), title="T")
    # Every chrome site follows color_accent: crosshair lines, toolbar
    # active state, hover icon fill, spike lines (initial layout + theme
    # toggle JS). The dark template's candlestick colors are chart data
    # styling, not chrome, and stay independent.
    assert "border-top: 1px dashed #ff8800" in html
    assert "border-left: 1px dashed #ff8800" in html
    assert "background-color: #ff8800 !important" in html
    assert "fill: #ff8800 !important" in html
    assert 'update[key + \'.spikecolor\'] = "#ff8800";' in html
    assert 'setCrosshairColor("#ff8800");' in html
    assert '"spikecolor":"#ff8800"' in html.replace('": "', '":"')
    assert "#4FC3F7" not in html


def test_table_value_colors_default_unchanged():
    html = _create_table_html(pd.DataFrame({"A": [1]}), title="T")
    assert "#00ACFF" in html
    assert "#e4003a" in html


def test_table_value_colors_follow_config():
    deskplot.configure(color_value_up="#11aa22", color_value_down="#bb3344")
    html = _create_table_html(pd.DataFrame({"A": [1]}), title="T")
    assert "#11aa22" in html
    assert "#bb3344" in html
    assert "#00ACFF" not in html
    assert "#e4003a" not in html


def test_browser_fallback_warns_loudly(monkeypatch, capsys):
    import deskplot.backend as backend_mod

    monkeypatch.setattr(backend_mod, "WEBVIEW_AVAILABLE", False)
    monkeypatch.setattr(backend_mod.Backend, "_instance", None)
    monkeypatch.setattr(backend_mod, "BACKEND", None)
    backend_mod.create_backend()
    out = capsys.readouterr().out
    # Native windows are the intended experience — the fallback must not
    # announce itself with a single easy-to-miss line
    assert "native windows" in out.lower()
    assert "pip install pywebview" in out
    assert out.count("\n") >= 4


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


def _title_div(html: str, title: str) -> str:
    """Return the style attribute of the header div holding the title."""
    for chunk in html.split("<div"):
        if f">{title}</div>" in chunk:
            return chunk
    raise AssertionError(f"no header div found for title {title!r}")


def test_chart_title_is_absolutely_centered():
    # Flex space-between centers the middle child between unequal flanks;
    # the title must be centered against the header itself instead.
    html = _create_chart_html(_fig(), title="Centered Title")
    style = _title_div(html, "Centered Title")
    assert "position: absolute" in style
    assert "left: 50%" in style
    assert "translateX(-50%)" in style
    assert "text-overflow: ellipsis" in style


def test_table_title_is_absolutely_centered():
    df = pd.DataFrame({"A": [1]})
    html = _create_table_html(df, title="Tbl Title")
    # .title is absolutely centered inside the (relative) #header
    assert "position: relative" in html.split("#header")[1].split("}")[0]
    title_css = html.split(".title {")[1].split("}")[0]
    assert "position: absolute" in title_css
    assert "left: 50%" in title_css
    assert "translateX(-50%)" in title_css
    assert "text-overflow: ellipsis" in title_css


def test_table_html_uses_default_brand():
    df = pd.DataFrame({"A": [1]})
    table = _create_table_html(df)
    assert '<div class="logo-text">deskplot</div>' in table
