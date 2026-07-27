"""deskplot - Plotly charts in native desktop windows.

Non-blocking, dark-themed, brandable chart windows for Python:

    import deskplot

    fig = deskplot.ChartFigure()
    fig.add_scatter(x=[1, 2, 3], y=[4, 1, 7])
    fig.show()          # opens a native window (or browser fallback)
"""

from deskplot.config import Config, configure, get_config
from deskplot.figure import ChartFigure, show_table
from deskplot.backend import create_backend, get_backend
from deskplot.style import ChartStyle, de_increasing_color_list

__version__ = "0.3.0"

__all__ = [
    "ChartFigure",
    "show_table",
    "configure",
    "get_config",
    "Config",
    "create_backend",
    "get_backend",
    "ChartStyle",
    "de_increasing_color_list",
    "__version__",
]
