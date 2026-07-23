"""Interactive DataFrame table: sortable columns, signed coloring, CSV export."""

import pandas as pd

import deskplot

df = pd.DataFrame(
    {
        "Market": ["ES", "NQ", "CL", "GC", "ZN", "6E"],
        "Position": [1.20, -0.45, 0.80, -1.10, 0.35, -0.20],
        "1d Change": [0.15, -0.08, 0.22, -0.31, 0.05, -0.02],
        "Signal": ["Long", "Short", "Long", "Short", "Long", "Short"],
    }
)

deskplot.show_table(df, title="Example Positioning Table", source="Synthetic data")
