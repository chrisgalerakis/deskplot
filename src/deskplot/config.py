"""Runtime configuration for deskplot.

All user-facing text and accent colors flow through a single mutable
:class:`Config` instance, read at render time — never baked into HTML at
import time. Customize via :func:`configure`:

    import deskplot
    deskplot.configure(brand="MY DESK", color_accent="#00ACFF", source="My Research")

Persistent configuration lives in a ``deskplot.toml`` file whose keys
mirror :class:`Config` fields as a flat table::

    brand = "MY DESK"
    color_accent = "#00ACFF"
    source = "My Research"

The file is discovered lazily on first :func:`get_config` /
:func:`configure` call, checking in order:

1. ``$DESKPLOT_CONFIG`` — explicit file path, wins when set;
2. ``deskplot.toml`` in the current working directory;
3. ``deskplot.toml`` in the per-user config directory (hand-rolled,
   no ``platformdirs`` dependency: ``%APPDATA%\\deskplot`` on Windows,
   ``~/Library/Application Support/deskplot`` on macOS,
   ``$XDG_CONFIG_HOME/deskplot`` or ``~/.config/deskplot`` elsewhere).

Precedence: dataclass defaults < ``deskplot.toml`` < ``configure()``
calls. Unknown keys and unreadable files warn instead of crashing.
"""

import os
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # Python 3.10 backport (conditional dependency)

CONFIG_FILENAME = "deskplot.toml"
CONFIG_PATH_ENV_VAR = "DESKPLOT_CONFIG"


@dataclass
class Config:
    """Global deskplot settings.

    Attributes:
        brand: Primary brand text shown in the window header bar.
        brand_secondary: Optional secondary brand text (rendered after a
            separator). Empty string hides it.
        color_brand: Color for the primary brand text (wordmark). ``None``
            (the default) falls back to ``color_primary``, so setting it is
            only needed to decouple the wordmark from the button color.
        color_primary: Accent color for the primary brand text and buttons.
        color_secondary: Color for the secondary brand text.
        color_accent: Accent color for window chrome: drawing tools (trend
            lines, shapes), hover spike lines, the custom crosshair, the
            toolbar active-button state, and toolbar icon hover fill.
        color_value_up: Color for positive numbers in the table viewer.
        color_value_down: Color for negative numbers in the table viewer.
        source: Default source attribution for charts and tables. Empty
            string means no attribution is rendered unless passed explicitly.
        auto_source: When True and ``source`` is set, ``ChartFigure.show()``
            automatically adds the source annotation (bottom-left) to any
            figure that doesn't have one. A per-figure source always wins:
            ``fig.add_source_annotation("X")`` or ``fig.show(source="X")``
            override the global text; ``fig.show(source=False)`` suppresses;
            auto never overwrites or duplicates an existing source.
        chart_title: Fallback window title for charts.
        table_title: Fallback window title for tables.
        export_prefix: Filename prefix for exported PNG/CSV files.
        window_title_format: Format string for native window titles.
            Receives ``{brand}`` and ``{title}``.
        show_header_timestamp: Render the live render-time timestamp in the
            window header bar (chart and table). Set False when it could be
            confused with a chart's own as-of date on screenshots.
        log_prefix: Prefix for console messages.
        axis_tick_font_size: Font size of x/y axis tick labels.
        axis_title_font_size: Font size of x/y axis titles.

    Set options before creating figures — they are applied when a
    ``ChartFigure`` is constructed.
    """

    brand: str = "deskplot"
    brand_secondary: str = ""
    color_brand: Optional[str] = None
    color_primary: str = "#5b9aff"
    color_secondary: str = "#e0e0e0"
    color_accent: str = "#5b9aff"
    color_value_up: str = "#00ACFF"
    color_value_down: str = "#e4003a"
    source: str = ""
    auto_source: bool = False
    chart_title: str = "Interactive Chart"
    table_title: str = "Data Table"
    export_prefix: str = "chart"
    window_title_format: str = "{brand} - {title}"
    show_header_timestamp: bool = True
    log_prefix: str = "[deskplot]"
    axis_tick_font_size: int = 11
    axis_title_font_size: int = 12


_config = Config()

# deskplot.toml is applied at most once per process, lazily on the first
# get_config()/configure() call — not at import time.
_file_config_loaded = False


def _user_config_dir() -> Path:
    """Per-user config directory for deskplot on the current platform."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "deskplot"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "deskplot"
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "deskplot"


def _find_config_file() -> Optional[Path]:
    """Locate deskplot.toml: $DESKPLOT_CONFIG > cwd > user config dir."""
    env_path = os.environ.get(CONFIG_PATH_ENV_VAR)
    if env_path:
        path = Path(env_path)
        if path.is_file():
            return path
        warnings.warn(
            f"deskplot: ${CONFIG_PATH_ENV_VAR} points to {path}, which does"
            " not exist; ignoring it",
            stacklevel=4,
        )
        return None
    for candidate in (
        Path.cwd() / CONFIG_FILENAME,
        _user_config_dir() / CONFIG_FILENAME,
    ):
        if candidate.is_file():
            return candidate
    return None


def _load_file_config() -> None:
    """Apply deskplot.toml (if any) to the global config, once."""
    global _file_config_loaded
    if _file_config_loaded:
        return
    _file_config_loaded = True

    path = _find_config_file()
    if path is None:
        return
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        warnings.warn(
            f"deskplot: could not read {path} ({exc}); using defaults",
            stacklevel=4,
        )
        return
    for key, value in data.items():
        if key not in Config.__dataclass_fields__:
            warnings.warn(
                f"deskplot: unknown option {key!r} in {path}; ignoring it",
                stacklevel=4,
            )
            continue
        setattr(_config, key, value)


def configure(**kwargs) -> Config:
    """Update deskplot's global configuration.

    Args:
        **kwargs: Any :class:`Config` field, e.g. ``brand="MY DESK"``.

    Returns:
        The updated global :class:`Config`.

    Raises:
        TypeError: If an unknown option is passed.
    """
    _load_file_config()
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
    _load_file_config()
    return _config
