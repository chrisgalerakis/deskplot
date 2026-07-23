"""Basic deskplot example: a line chart in a native window."""

import numpy as np
import pandas as pd

import deskplot

rng = np.random.default_rng(42)
dates = pd.date_range("2025-01-01", periods=250, freq="B")
prices = 5000 + rng.normal(0, 25, len(dates)).cumsum()

fig = deskplot.ChartFigure()
fig.add_scatter(x=dates, y=prices, name="Index", line=dict(color="#00ACFF", width=1.5))
fig.add_hline_with_label(y=prices.mean(), label="Mean", line_color="#888888")
fig.set_title("Synthetic Index — Basic Chart")
fig.add_source_annotation("Synthetic data")
fig.show()
