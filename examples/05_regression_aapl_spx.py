"""Scatter regression: AAPL daily returns vs S&P 500 (beta, alpha, R-squared).

Fetches two years of real market data with yfinance when it is installed
(``pip install yfinance``); otherwise falls back to synthetic data so the
example always runs, even offline.
"""

import numpy as np
import pandas as pd

import deskplot


def load_returns():
    """Return (spx_returns_pct, aapl_returns_pct, source_label)."""
    try:
        import yfinance as yf

        px = yf.download(
            ["AAPL", "^GSPC"], period="2y", auto_adjust=True, progress=False
        )["Close"].dropna()
        rets = px.pct_change().dropna() * 100
        # yf.download swallows failures and returns NaN columns, which
        # dropna() reduces to zero rows — route that to the fallback too.
        if len(rets) < 2:
            raise ValueError("no overlapping return data downloaded")
        return rets["^GSPC"], rets["AAPL"], "Yahoo Finance, 2y daily"
    except Exception:
        rng = np.random.default_rng(3)
        idx = pd.date_range("2024-01-01", periods=500, freq="B")
        spx = rng.normal(0.04, 1.1, len(idx))
        aapl = 0.05 + 1.25 * spx + rng.normal(0, 1.0, len(idx))
        return (
            pd.Series(spx, idx),
            pd.Series(aapl, idx),
            "Synthetic data (yfinance unavailable)",
        )


def build_figure() -> deskplot.ChartFigure:
    x, y, source = load_returns()

    beta, alpha = np.polyfit(x, y, 1)
    r_squared = np.corrcoef(x, y)[0, 1] ** 2
    line_x = np.linspace(x.min(), x.max(), 100)

    fig = deskplot.ChartFigure()
    fig.add_scatter(
        x=x, y=y, mode="markers", name="Daily returns",
        marker=dict(color="#00ACFF", size=5, opacity=0.55),
        hovertemplate="S&P 500: %{x:.2f}%<br>AAPL: %{y:.2f}%<extra></extra>",
    )
    fig.add_scatter(
        x=line_x, y=alpha + beta * line_x, mode="lines",
        name=f"OLS fit (β={beta:.2f})",
        line=dict(color="#FF6B00", width=2),
    )
    fig.update_layout(
        xaxis_title="S&P 500 daily return (%)",
        yaxis_title="AAPL daily return (%)",
    )
    fig.set_title(
        f"AAPL vs S&P 500 — β={beta:.2f}, "
        f"α={alpha:.3f}%/day, R²={r_squared:.2f}"
    )
    fig.add_source_annotation(source)
    return fig


if __name__ == "__main__":
    build_figure().show()
