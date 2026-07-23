"""Runtime configuration for deskplot.

All user-facing text and accent colors flow through a single mutable
:class:`Config` instance, read at render time — never baked into HTML at
import time. Customize via :func:`configure`:

    import deskplot
    deskplot.configure(brand="MY DESK", color_accent="#00ACFF", source="My Research")
"""

from dataclasses import dataclass


@dataclass
class Config:
    """Global deskplot settings.

    Attributes:
        brand: Primary brand text shown in the window header bar.
        brand_secondary: Optional secondary brand text (rendered after a
            separator). Empty string hides it.
        color_primary: Accent color for the primary brand text and buttons.
        color_secondary: Color for the secondary brand text.
        color_accent: Accent color for drawing tools (trend lines, shapes).
        source: Default source attribution for charts and tables. Empty
            string means no attribution is rendered unless passed explicitly.
        chart_title: Fallback window title for charts.
        table_title: Fallback window title for tables.
        export_prefix: Filename prefix for exported PNG/CSV files.
        window_title_format: Format string for native window titles.
            Receives ``{brand}`` and ``{title}``.
        log_prefix: Prefix for console messages.
        axis_tick_font_size: Font size of x/y axis tick labels.
        axis_title_font_size: Font size of x/y axis titles.

    Set options before creating figures — they are applied when a
    ``ChartFigure`` is constructed.
    """

    brand: str = "deskplot"
    brand_secondary: str = ""
    color_primary: str = "#5b9aff"
    color_secondary: str = "#e0e0e0"
    color_accent: str = "#5b9aff"
    source: str = ""
    chart_title: str = "Interactive Chart"
    table_title: str = "Data Table"
    export_prefix: str = "chart"
    window_title_format: str = "{brand} - {title}"
    log_prefix: str = "[deskplot]"
    axis_tick_font_size: int = 11
    axis_title_font_size: int = 12


_config = Config()


def configure(**kwargs) -> Config:
    """Update deskplot's global configuration.

    Args:
        **kwargs: Any :class:`Config` field, e.g. ``brand="MY DESK"``.

    Returns:
        The updated global :class:`Config`.

    Raises:
        TypeError: If an unknown option is passed.
    """
    for key, value in kwargs.items():
        if not hasattr(_config, key):
            valid = ", ".join(Config.__dataclass_fields__)
            raise TypeError(
                f"Unknown deskplot config option {key!r}. Valid options: {valid}"
            )
        setattr(_config, key, value)
    return _config


def get_config() -> Config:
    """Return the global :class:`Config` instance."""
    return _config
