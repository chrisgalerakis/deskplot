"""Custom branding: put your own name and colors on every window."""

import numpy as np
import pandas as pd

import deskplot

deskplot.configure(
    brand="ACME RESEARCH",
    brand_secondary="MACRO DESK",
    color_primary="#00C853",
    source="ACME Research",
    export_prefix="acme_chart",
)

rng = np.random.default_rng(1)
dates = pd.date_range("2025-01-01", periods=120, freq="B")
values = rng.normal(0, 1, len(dates)).cumsum()

fig = deskplot.ChartFigure()
fig.add_scatter(x=dates, y=values, name="Strategy PnL", line=dict(color="#00C853"))
fig.set_title("Branded Chart Window")
fig.add_source_annotation()  # uses the configured source
fig.show()
