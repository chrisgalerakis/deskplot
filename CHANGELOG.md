# Changelog

All notable changes to deskplot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/).

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
