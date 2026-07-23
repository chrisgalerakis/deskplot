# Contributing to deskplot

Thanks for your interest — issues and pull requests are welcome.

## Development setup

```bash
git clone https://github.com/chrisgalerakis/deskplot
cd deskplot
pip install -e ".[dev,native]"
```

## Before opening a PR

```bash
ruff check src tests examples   # lint
pytest                          # 27+ tests, all must pass
```

- Keep changes focused — one logical change per PR.
- New behavior needs a test (the suite runs without pywebview or a display,
  so test the generated HTML rather than the window itself).
- The generated chart/table HTML must stay **offline-safe**: no CDN
  `<script src>` tags — vendor anything the page needs.
- Anything interpolated into generated JS must be JSON-encoded (see
  `_create_table_html` for the pattern).

## Reporting bugs

Please include your OS, Python version, whether pywebview is installed
(`pip show pywebview`), and a minimal script that reproduces the problem.

## Platform notes

Native windows depend on [pywebview](https://pywebview.flowrl.com/)'s
platform backends (WebKit on macOS, WebView2 on Windows, GTK/Qt on Linux).
Platform-specific fixes are especially appreciated — CI covers Ubuntu,
macOS, and Windows, but real-window behavior can only be tested by hand.
