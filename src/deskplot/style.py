"""Chart styling and theming for deskplot.

Registers a dark Plotly template ("deskplot_dark") layered on top of
``plotly_dark``, loaded from ``styles/dark.pltstyle.json``.

The ``.pltstyle.json`` theming approach follows the pattern established by
OpenBB Terminal (MIT licensed) — see the project README for attribution.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import plotly.graph_objects as go
import plotly.io as pio

from deskplot.config import get_config

# Style constants
PLT_STYLE_TEMPLATE = "plotly_dark"
PLT_STYLE_INCREASING = "#00ACFF"
PLT_STYLE_DECREASING = "#e4003a"
PLT_STYLE_INCREASING_GREEN = "#009600"
PLT_STYLE_DECREASING_RED = "#c80000"

# =============================================================================
# THEME-SAFE COLORS (visible on BOTH dark and light backgrounds)
# =============================================================================
# When picking trace colors, prefer these — they stay legible after the
# in-window theme toggle. Avoid #FFFFFF (white) and #000000 (black): each
# becomes invisible on one of the two themes.
# =============================================================================
THEME_SAFE_PRIMARY = "#00ACFF"      # Cyan - primary accent, works on both themes
THEME_SAFE_SECONDARY = "#e4003a"    # Red - negative/decreasing values
THEME_SAFE_ACCENT = "#FF6B00"       # Orange - secondary accent for data series
THEME_SAFE_REFERENCE = "#888888"    # Gray - reference lines (zero lines, etc.)
THEME_SAFE_POSITIVE = "#00C853"     # Green - positive indicators
THEME_SAFE_HIGHLIGHT = "#FFEB3B"    # Yellow - highlights/warnings

PLT_FONT = dict(family="JetBrains Mono, monospace", size=13)

PLT_COLORWAY = [
    "#ffed00",
    "#ef7d00",
    "#e4003a",
    "#c13246",
    "#822661",
    "#48277c",
    "#005ca9",
    "#00aaff",
    "#9b30d9",
    "#af005f",
    "#5f00af",
    "#af87ff",
]

# Table styling
PLT_TBL_HEADER = dict(
    fill_color="rgb(30, 30, 30)",
    font_color="white",
    line_color="#6e6e6e",
    line_width=1,
)
PLT_TBL_CELLS = dict(
    font_color="white",
    line_color="#6e6e6e",
    line_width=0,
)
PLT_TBL_ROW_COLORS = (
    "#333333",
    "#242424",
)

# Candlestick styling
PLT_CANDLESTICKS = dict(
    increasing=dict(line_color=PLT_STYLE_INCREASING, fillcolor=PLT_STYLE_INCREASING),
    decreasing=dict(line_color=PLT_STYLE_DECREASING, fillcolor=PLT_STYLE_DECREASING),
)

STYLES_REPO = Path(__file__).parent / "styles"


class ChartStyle:
    """Singleton class for managing chart styling."""

    _instance: Optional["ChartStyle"] = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, style: str = "dark"):
        """Initialize chart style.

        Args:
            style: Theme name (currently only 'dark' ships with deskplot)
        """
        if self._initialized:
            return

        self.style = style
        self.plotly_template: Dict[str, Any] = {}
        self.up_color = PLT_STYLE_INCREASING
        self.down_color = PLT_STYLE_DECREASING
        self.line_color = "#ffed00"
        self.line_width = 1.5

        self.load_style(style)
        self.apply_style()
        self._initialized = True

    def load_style(self, style: str = "dark") -> None:
        """Load style from JSON file.

        Args:
            style: Theme name
        """
        style_path = STYLES_REPO / f"{style}.pltstyle.json"

        if not style_path.exists():
            print(f"Style file not found: {style_path}, using defaults")
            return

        with open(style_path, "r") as f:
            self.plotly_template = json.load(f)

        # Extract line styling
        line = self.plotly_template.pop("line", {})
        self.up_color = line.get("up_color", PLT_STYLE_INCREASING)
        self.down_color = line.get("down_color", PLT_STYLE_DECREASING)
        self.line_color = line.get("color", "#ffed00")
        self.line_width = line.get("width", 1.5)

    def apply_style(self) -> None:
        """Register custom template with Plotly."""
        if self.plotly_template:
            # Inject configured axis font sizes so axes added after figure
            # construction (e.g. a late secondary y-axis) still match.
            # Idempotent: ChartFigure re-invokes this at each construction
            # to pick up configure() changes.
            cfg = get_config()
            layout_tpl = self.plotly_template.setdefault("layout", {})
            for axis_name in ("xaxis", "yaxis"):
                axis = layout_tpl.setdefault(axis_name, {})
                axis.setdefault("tickfont", {})["size"] = cfg.axis_tick_font_size
                axis.setdefault("title_font", {})["size"] = cfg.axis_title_font_size
            pio.templates["deskplot_dark"] = go.layout.Template(self.plotly_template)
            pio.templates.default = "plotly_dark+deskplot_dark"
        else:
            pio.templates.default = "plotly_dark"

    def get_colors(self) -> Dict[str, str]:
        """Get current color scheme."""
        return {
            "up": self.up_color,
            "down": self.down_color,
            "line": self.line_color,
            "background": "#06080e",
            "grid": "rgba(255,255,255,0.05)",
            "text": "#6b7080",
        }


def get_chart_style() -> ChartStyle:
    """Get or create the chart style singleton."""
    return ChartStyle()


def de_increasing_color_list(
    values,
    increasing_color: str = PLT_STYLE_INCREASING,
    decreasing_color: str = PLT_STYLE_DECREASING,
):
    """Generate color list based on positive/negative values.

    Args:
        values: Iterable of numeric values
        increasing_color: Color for positive values
        decreasing_color: Color for negative values

    Returns:
        List of colors
    """
    return [
        increasing_color if v >= 0 else decreasing_color
        for v in values
    ]
