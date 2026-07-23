import pandas as pd
import plotly.graph_objects as go

import deskplot
from deskplot import ChartFigure


def test_default_layout_applied():
    fig = ChartFigure()
    assert fig.layout.template is not None
    assert fig.layout.paper_bgcolor == "#06080e"
    assert fig.layout.plot_bgcolor == "#06080e"
    assert fig.layout.font.family == "JetBrains Mono, monospace"


def test_set_title_chains_and_sets_layout():
    fig = ChartFigure().set_title("Hello")
    assert isinstance(fig, ChartFigure)
    assert fig.layout.title.text == "Hello"


def test_source_annotation_noop_when_unset():
    fig = ChartFigure()
    fig.add_source_annotation()
    assert len(fig.layout.annotations) == 0


def test_source_annotation_explicit():
    fig = ChartFigure()
    fig.add_source_annotation("Bloomberg", include_date=False)
    texts = [a.text for a in fig.layout.annotations]
    assert "Source: Bloomberg" in texts


def test_source_annotation_uses_configured_default():
    deskplot.configure(source="My Desk")
    fig = ChartFigure()
    fig.add_source_annotation(include_date=False)
    texts = [a.text for a in fig.layout.annotations]
    assert "Source: My Desk" in texts


def test_axis_font_sizes_default():
    fig = ChartFigure()
    assert fig.layout.xaxis.tickfont.size == 11
    assert fig.layout.yaxis.title.font.size == 12


def test_axis_font_sizes_configurable():
    deskplot.configure(axis_tick_font_size=16, axis_title_font_size=18)
    fig = ChartFigure()
    assert fig.layout.xaxis.tickfont.size == 16
    assert fig.layout.yaxis.tickfont.size == 16
    assert fig.layout.xaxis.title.font.size == 18
    assert fig.layout.yaxis.title.font.size == 18


def test_reconfigure_after_first_figure_updates_template():
    import plotly.io as pio

    ChartFigure()  # initializes the style singleton, baking current sizes
    deskplot.configure(axis_tick_font_size=16)
    ChartFigure()  # must re-sync the registered template
    assert pio.templates["deskplot_dark"].layout.yaxis.tickfont.size == 16
    assert pio.templates["deskplot_dark"].layout.xaxis.tickfont.size == 16


def test_axis_font_sizes_apply_to_all_subplot_axes():
    deskplot.configure(axis_tick_font_size=15)
    fig = ChartFigure.create_subplots(rows=2, cols=1)
    assert fig.layout.yaxis.tickfont.size == 15
    assert fig.layout.yaxis2.tickfont.size == 15
    assert fig.layout.xaxis2.tickfont.size == 15


def _shown_quietly(fig, monkeypatch, **kwargs):
    monkeypatch.setattr("deskplot.backend.webbrowser.open", lambda url: None)
    fig.show(external=True, **kwargs)
    return [a.text for a in fig.layout.annotations if a.text and "Source:" in a.text]


def test_auto_source_off_by_default(monkeypatch):
    deskplot.configure(source="Vendor")
    fig = ChartFigure()
    assert _shown_quietly(fig, monkeypatch) == []


def test_auto_source_adds_annotation_once(monkeypatch):
    deskplot.configure(source="Vendor", auto_source=True)
    fig = ChartFigure()
    assert len(_shown_quietly(fig, monkeypatch)) == 1
    # Second show must not duplicate
    assert len(_shown_quietly(fig, monkeypatch)) == 1


def test_auto_source_noop_without_source(monkeypatch):
    deskplot.configure(auto_source=True)  # source stays ""
    fig = ChartFigure()
    assert _shown_quietly(fig, monkeypatch) == []


def test_show_source_false_suppresses(monkeypatch):
    deskplot.configure(source="Vendor", auto_source=True)
    fig = ChartFigure()
    assert _shown_quietly(fig, monkeypatch, source=False) == []


def test_show_source_true_forces(monkeypatch):
    deskplot.configure(source="Vendor")  # auto_source off
    fig = ChartFigure()
    assert len(_shown_quietly(fig, monkeypatch, source=True)) == 1


def test_explicit_annotation_beats_global_auto(monkeypatch):
    deskplot.configure(source="Global Vendor", auto_source=True)
    fig = ChartFigure()
    fig.add_source_annotation("Per-Chart Vendor", include_date=False)
    texts = _shown_quietly(fig, monkeypatch)
    assert texts == ["Source: Per-Chart Vendor"]  # not duplicated, not global


def test_show_source_string_sets_per_chart_source(monkeypatch):
    deskplot.configure(source="Global Vendor", auto_source=True)
    fig = ChartFigure()
    texts = _shown_quietly(fig, monkeypatch, source="Bloomberg L.P.")
    assert len(texts) == 1 and texts[0].startswith("Source: Bloomberg L.P.")


def test_show_source_empty_string_suppresses(monkeypatch):
    deskplot.configure(source="Global Vendor", auto_source=True)
    fig = ChartFigure()
    assert _shown_quietly(fig, monkeypatch, source="") == []


def test_show_source_string_does_not_override_explicit(monkeypatch):
    deskplot.configure(auto_source=True, source="Global Vendor")
    fig = ChartFigure()
    fig.add_source_annotation("First Wins", include_date=False)
    texts = _shown_quietly(fig, monkeypatch, source="Second Ignored")
    assert texts == ["Source: First Wins"]


def test_wrapped_pre_annotated_figure_not_double_stamped(monkeypatch):
    deskplot.configure(source="Global Vendor", auto_source=True)
    inner = ChartFigure()
    inner.add_source_annotation("Inner Vendor", include_date=False)
    wrapped = ChartFigure(fig=inner)  # fresh _source_added flag
    texts = _shown_quietly(wrapped, monkeypatch)
    assert texts == ["Source: Inner Vendor"]


def test_hline_with_label():
    fig = ChartFigure().add_hline_with_label(y=5.0, label="Level")
    assert any(a.text == "Level" for a in fig.layout.annotations)
    assert len(fig.layout.shapes) == 1


def test_create_subplots_returns_chartfigure():
    fig = ChartFigure.create_subplots(rows=2, cols=1, shared_xaxes=True)
    assert isinstance(fig, ChartFigure)
    fig.add_scatter(y=[1, 2], row=1, col=1)
    fig.add_scatter(y=[3, 4], row=2, col=1)
    assert len(fig.data) == 2


def test_to_table_builds_table_trace():
    df = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
    fig = ChartFigure.to_table(df, title="T")
    assert len(fig.data) == 1
    assert isinstance(fig.data[0], go.Table)


def test_to_html_returns_string():
    fig = ChartFigure()
    fig.add_scatter(y=[1, 2, 3])
    html = fig.to_html(include_plotlyjs=False)
    assert isinstance(html, str)
    assert "plotly" in html.lower()


def test_wraps_existing_plotly_figure():
    base = go.Figure()
    base.add_scatter(y=[1, 2, 3])
    fig = ChartFigure(fig=base)
    assert len(fig.data) == 1
