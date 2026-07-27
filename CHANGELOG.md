# Changelog

All notable changes to deskplot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/).

## [0.3.0] - 2026-07-27

### Added
- `deskplot.toml` config file support: persistent configuration without
  `configure()` calls. Discovered on first use from `$DESKPLOT_CONFIG`
  (explicit path, wins), the current working directory, or the per-user
  config dir (`%APPDATA%\deskplot`, `~/Library/Application
  Support/deskplot`, or `$XDG_CONFIG_HOME`/`~/.config/deskplot`). Flat
  keys mirror `Config` fields; precedence is defaults < file <
  `configure()`; unknown keys and bad TOML warn instead of crashing.
  Uses stdlib `tomllib` (with the `tomli` backport on Python 3.10).
- `color_brand` config option: color for the brand text (wordmark) in
  chart and table headers, decoupled from the button/control color.
  Defaults to `None` = fall back to `color_primary` (no visual change).
- `show_header_timestamp` config option (default `True`): set `False` to
  drop the render-time timestamp from the header bar — useful when it
  could be confused with a chart's own as-of date on screenshots.
- `color_value_up` / `color_value_down` config options for the table
  viewer's signed-value colors (defaults unchanged: `#00ACFF`/`#e4003a`).

### Changed
- Window chrome colors now follow `configure()` instead of hardcoded
  hexes: hover spike lines, the custom crosshair, the toolbar
  active-button state, and toolbar icon hover fill all use
  `color_accent`. Note: these were previously hardcoded `#00ACFF`/
  `#4FC3F7`; with the default config they now render in deskplot's
  accent `#5b9aff` — set `color_accent = "#00ACFF"` to restore the old
  shade. Toolbar surface colors are hoisted to module-level constants.
- pywebview is now a default dependency: a plain `pip install deskplot`
  opens native desktop windows with no extras. Native windows are
  deskplot's purpose; the browser fallback remains only as graceful
  degradation (headless boxes, SSH, missing OS webview) and now announces
  itself with a loud multi-line warning instead of a single console line.
- The `deskplot[native]` extra is deprecated and now a no-op alias; it
  will be removed in a future release.

### Fixed
- Window title is now truly centered in chart and table headers. It was
  previously centered between two unequal flex flanks (brand block vs
  timestamp/buttons), rendering visibly off-center in live windows and
  exported PNGs. Long titles now ellipsize instead of colliding with the
  header controls.

## [0.2.0] - 2026-07-23

### Added
- `auto_source` config option (default off): when enabled together with a
  configured `source`, `ChartFigure.show()` automatically adds the
  bottom-left source annotation to figures that don't already have one
  (never duplicated across repeated shows). Per-figure override:
  `fig.show(source=True)` forces it, `fig.show(source=False)` suppresses.

### Fixed
- Windows CI: two test-suite portability bugs (file-URI→path conversion,
  UTF-8 read of generated HTML). Package code unaffected.

### Changed
- README: absolute image/link URLs so the PyPI project page renders
  correctly; native-window hero banner; post-launch cleanups.

## [0.1.0] - 2026-07-23

Initial public release.

### Added
- `ChartFigure`: Plotly `go.Figure` subclass with terminal-dark defaults,
  chainable helpers (`set_title`, `add_hline_with_label`,
  `add_vline_with_label`, `add_source_annotation`, `horizontal_legend`),
  subplot factory (`create_subplots`), and DataFrame table builder (`to_table`).
- Native window backend: each `fig.show()` opens a non-blocking pywebview
  window in its own subprocess; browser fallback when pywebview is absent.
- In-window chrome: brandable header bar, grouped bottom-centered toolbar,
  dark/light theme toggle, crosshair cursor, unified-hover toggle, and
  header-inclusive PNG export (vendored html2canvas, offline-safe).
- `show_table`: sortable dark-themed DataFrame viewer with CSV export.
- `deskplot.configure()`: runtime branding and configuration — brand text,
  colors, source attribution (hidden when blank), export prefix, window
  title format, and axis font sizes (`axis_tick_font_size`,
  `axis_title_font_size`) applied to every axis including subplots.
- Dark Plotly template loaded from `styles/dark.pltstyle.json`.
- Examples: basic chart, subplots with dual axis, interactive table,
  custom branding, and an AAPL vs S&P 500 daily-return regression
  (yfinance data with synthetic offline fallback).
- `py.typed` marker (PEP 561) — type checkers consume deskplot's
  annotations.
- Packaging (`pyproject.toml`, src layout), test suite, CI
  (Linux/macOS/Windows × Python 3.10–3.13), CONTRIBUTING and RELEASING
  docs.
