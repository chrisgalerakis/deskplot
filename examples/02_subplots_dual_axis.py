"""Subplots with a secondary y-axis: price panel + volume panel."""

import numpy as np
import pandas as pd

import deskplot

rng = np.random.default_rng(7)
dates = pd.date_range("2025-01-01", periods=250, freq="B")
price = 100 + rng.normal(0, 1.2, len(dates)).cumsum()
signal = pd.Series(price).rolling(20).mean()
volume = rng.integers(1_000, 12_000, len(dates))

fig = deskplot.ChartFigure.create_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    row_heights=[0.72, 0.28],
    specs=[[{"secondary_y": True}], [{}]],
)
fig.add_scatter(x=dates, y=price, name="Price", line=dict(color="#00ACFF"), row=1, col=1)
fig.add_scatter(x=dates, y=signal, name="20d MA", line=dict(color="#FF6B00", dash="dot"), row=1, col=1)
fig.add_bar(x=dates, y=volume, name="Volume", marker_color="#888888", row=2, col=1)
fig.show(title="Price, Moving Average & Volume")
