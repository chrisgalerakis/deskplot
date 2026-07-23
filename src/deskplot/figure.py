"""ChartFigure - Custom Plotly Figure class with native window integration."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from deskplot.backend import get_backend
from deskplot.config import get_config
from deskplot.style import (
    PLT_TBL_HEADER,
    PLT_TBL_CELLS,
    PLT_TBL_ROW_COLORS,
    get_chart_style,
)


class ChartFigure(go.Figure):
    """Custom Plotly Figure class with native window backend support."""

    def __init__(
        self,
        fig: Optional[go.Figure] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ChartFigure.

        Args:
            fig: Optional existing figure to wrap
            **kwargs: Additional arguments passed to go.Figure
        """
        super().__init__(**kwargs)

        if fig is not None:
            # Copy first so applying the deskplot theme never mutates the
            # caller's original figure.
            self.__dict__.update(go.Figure(fig).__dict__)

        # Initialize styling; re-register the template so config changes
        # made since the last figure (e.g. axis font sizes) are picked up
        self._style = get_chart_style()
        self._style.apply_style()
        self._title = ""
        self._source = get_config().source

        # Apply default layout
        self._apply_default_layout()

    def _apply_default_layout(self) -> None:
        """Apply default layout settings.

        Standalone viewer uses slightly larger fonts/margins for readability.
        """
        self.update_layout(
            template="plotly_dark+deskplot_dark",
            paper_bgcolor="#06080e",
            plot_bgcolor="#06080e",
            font=dict(family="JetBrains Mono, monospace", size=13, color="#6b7080"),
            margin=dict(l=60, r=60, t=80, b=60),
            legend=dict(
                orientation="h",
                yanchor="bottom", y=1.0, xanchor="center", x=0.5,
                bgcolor="rgba(0,0,0,0)",
                font=dict(size=10, color="#888"),
                itemclick="toggle", itemdoubleclick="toggleothers",
            ),
            hoverlabel=dict(
                bgcolor="#1c1c1c",
                bordercolor="#3a3a3a",
                font=dict(size=11, family="JetBrains Mono, monospace", color="#e0e0e0"),
            ),
            newshape=dict(
                line=dict(color="#f0c040", width=2),
                fillcolor="rgba(240,192,64,0.12)",
            ),
            xaxis=dict(
                gridcolor="rgba(255,255,255,0.05)",
                griddash="dot",
                gridwidth=0.5,
                zerolinecolor="rgba(255,255,255,0.08)",
                showline=False,
                showgrid=True,
            ),
            yaxis=dict(
                gridcolor="rgba(255,255,255,0.05)",
                griddash="dot",
                gridwidth=0.5,
                zerolinecolor="rgba(255,255,255,0.08)",
                showline=False,
                showgrid=True,
                side="right",
            ),
        )

        # Configurable axis font sizes; update_x/yaxes reaches every axis
        # present at construction (all subplot panels included)
        cfg = get_config()
        self.update_xaxes(
            tickfont_size=cfg.axis_tick_font_size,
            title_font_size=cfg.axis_title_font_size,
        )
        self.update_yaxes(
            tickfont_size=cfg.axis_tick_font_size,
            title_font_size=cfg.axis_title_font_size,
        )

    @classmethod
    def create_subplots(
        cls,
        rows: int = 1,
        cols: int = 1,
        shared_xaxes: bool = False,
        shared_yaxes: bool = False,
        vertical_spacing: float = 0.1,
        horizontal_spacing: float = 0.1,
        row_heights: Optional[List[float]] = None,
        column_widths: Optional[List[float]] = None,
        specs: Optional[List[List[Dict]]] = None,
        subplot_titles: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> "ChartFigure":
        """Create a ChartFigure with subplots.

        Args:
            rows: Number of rows
            cols: Number of columns
            shared_xaxes: Share x-axes
            shared_yaxes: Share y-axes
            vertical_spacing: Vertical spacing between subplots
            horizontal_spacing: Horizontal spacing between subplots
            row_heights: Relative heights of rows
            column_widths: Relative widths of columns
            specs: Subplot specs (for secondary_y, etc.)
            subplot_titles: Titles for each subplot

        Returns:
            ChartFigure with subplots configured
        """
        fig = make_subplots(
            rows=rows,
            cols=cols,
            shared_xaxes=shared_xaxes,
            shared_yaxes=shared_yaxes,
            vertical_spacing=vertical_spacing,
            horizontal_spacing=horizontal_spacing,
            row_heights=row_heights,
            column_widths=column_widths,
            specs=specs,
            subplot_titles=subplot_titles,
            **kwargs,
        )

        return cls(fig=fig)

    def set_title(self, title: str, **kwargs: Any) -> "ChartFigure":
        """Set the figure title.

        Args:
            title: Title text
            **kwargs: Additional title formatting options

        Returns:
            Self for chaining
        """
        self._title = title
        self.update_layout(
            title=dict(
                text=title,
                x=0.5,
                xanchor="center",
                font=dict(size=14, color="#e0e0e0"),
                **kwargs,
            )
        )
        return self

    def add_source_annotation(
        self,
        source: Optional[str] = None,
        include_date: bool = True,
    ) -> "ChartFigure":
        """Add source attribution annotation.

        Args:
            source: Source text (defaults to the configured ``source``; if
                neither is set, no annotation is added)
            include_date: Include current date

        Returns:
            Self for chaining
        """
        source = source or get_config().source
        if not source:
            return self
        self._source = source
        text = f"Source: {source}"
        if include_date:
            text += f" | {datetime.now().strftime('%Y/%m/%d')}"

        self.add_annotation(
            x=0.01,
            y=-0.08,
            xref="paper",
            yref="paper",
            text=text,
            showarrow=False,
            font=dict(size=10, color="#888888"),
            xanchor="left",
        )
        return self

    def add_hline_with_label(
        self,
        y: float,
        label: str,
        line_color: str = "white",
        line_dash: str = "dash",
        line_width: float = 1,
        **kwargs: Any,
    ) -> "ChartFigure":
        """Add horizontal line with label.

        Args:
            y: Y-value for the line
            label: Label text
            line_color: Line color
            line_dash: Line dash style
            line_width: Line width

        Returns:
            Self for chaining
        """
        self.add_hline(
            y=y,
            line=dict(color=line_color, dash=line_dash, width=line_width),
            **kwargs,
        )
        self.add_annotation(
            x=1.02,
            y=y,
            xref="paper",
            yref="y",
            text=label,
            showarrow=False,
            font=dict(size=10, color=line_color),
            xanchor="left",
        )
        return self

    def add_vline_with_label(
        self,
        x: float,
        label: str,
        line_color: str = "white",
        line_dash: str = "dash",
        line_width: float = 1,
        **kwargs: Any,
    ) -> "ChartFigure":
        """Add vertical line with label.

        Args:
            x: X-value for the line
            label: Label text
            line_color: Line color
            line_dash: Line dash style
            line_width: Line width

        Returns:
            Self for chaining
        """
        self.add_vline(
            x=x,
            line=dict(color=line_color, dash=line_dash, width=line_width),
            **kwargs,
        )
        self.add_annotation(
            x=x,
            y=1.02,
            xref="x",
            yref="paper",
            text=label,
            showarrow=False,
            font=dict(size=9, color=line_color),
            yanchor="bottom",
        )
        return self

    def horizontal_legend(
        self,
        y: float = 1.02,
        xanchor: str = "center",
        orientation: str = "h",
    ) -> "ChartFigure":
        """Position legend horizontally above the chart.

        Args:
            y: Y position
            xanchor: X anchor
            orientation: Legend orientation

        Returns:
            Self for chaining
        """
        self.update_layout(
            legend=dict(
                orientation=orientation,
                yanchor="bottom",
                y=y,
                xanchor=xanchor,
                x=0.5,
            )
        )
        return self

    @classmethod
    def to_table(
        cls,
        df: pd.DataFrame,
        title: str = "",
        column_width: Optional[List[float]] = None,
        height: int = 600,
        width: int = 1000,
    ) -> "ChartFigure":
        """Create an interactive table from a DataFrame.

        Args:
            df: DataFrame to display
            title: Table title
            column_width: Custom column widths
            height: Table height
            width: Table width

        Returns:
            ChartFigure containing the table
        """
        # Prepare header
        header_values = [f"<b>{col}</b>" for col in df.columns]

        # Prepare cell values (transpose for Plotly)
        cell_values = [df[col].tolist() for col in df.columns]

        # Calculate column widths if not provided
        if column_width is None:
            column_width = [
                max(len(str(col)), df[col].astype(str).str.len().max())
                for col in df.columns
            ]
            total = sum(column_width)
            column_width = [w / total for w in column_width]

        # Generate alternating row colors
        n_rows = len(df)
        row_colors = [
            PLT_TBL_ROW_COLORS[i % 2] for i in range(n_rows)
        ]
        # Transpose for cell fill
        cell_fill_colors = [row_colors for _ in df.columns]

        fig = cls()
        fig.add_trace(
            go.Table(
                header=dict(
                    values=header_values,
                    fill_color=PLT_TBL_HEADER["fill_color"],
                    font=dict(color=PLT_TBL_HEADER["font_color"], size=12),
                    line_color=PLT_TBL_HEADER["line_color"],
                    line_width=PLT_TBL_HEADER["line_width"],
                    align="center",
                    height=30,
                ),
                cells=dict(
                    values=cell_values,
                    fill_color=cell_fill_colors,
                    font=dict(color=PLT_TBL_CELLS["font_color"], size=11),
                    line_color=PLT_TBL_CELLS["line_color"],
                    line_width=PLT_TBL_CELLS["line_width"],
                    align="left",
                    height=25,
                ),
                columnwidth=column_width,
            )
        )

        fig.update_layout(
            title=dict(
                text=title,
                x=0.5,
                xanchor="center",
                font=dict(size=16, color="white"),
            ),
            height=height,
            width=width,
            margin=dict(l=10, r=10, t=60, b=10),
        )

        return fig

    def show(
        self,
        title: Optional[str] = None,
        external: bool = False,
        **kwargs: Any,
    ) -> None:
        """Display the figure in a native window.

        Args:
            title: Window title override
            external: Force browser display instead of native window
        """
        backend = get_backend()

        if external:
            # Force browser-based display
            backend._show_in_browser(
                self, title or self._title or get_config().chart_title
            )
        else:
            # Use native window (pywebview)
            backend.send_figure(
                fig=self,
                title=title or self._title,
            )

    def to_html(
        self,
        path: Optional[str] = None,
        full_html: bool = True,
        include_plotlyjs: Union[bool, str] = True,
        config: Optional[dict] = None,
    ) -> Optional[str]:
        """Export figure to HTML.

        Args:
            path: Output file path (if None, returns HTML string)
            full_html: Include full HTML document structure
            include_plotlyjs: Include Plotly.js library
            config: Plotly config dict (e.g. {"scrollZoom": True})

        Returns:
            HTML string if path is None, else None
        """
        kwargs = dict(
            full_html=full_html,
            include_plotlyjs=include_plotlyjs,
        )
        if config is not None:
            kwargs["config"] = config
        html = pio.to_html(self, **kwargs)

        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            return None

        return html

    def save_image(
        self,
        path: str,
        format: str = "png",
        width: int = 1920,
        height: int = 1080,
        scale: int = 2,
    ) -> None:
        """Save figure as image.

        Requires the ``kaleido`` package (``pip install "deskplot[image]"``).

        Args:
            path: Output file path
            format: Image format (png, svg, pdf, jpeg)
            width: Image width
            height: Image height
            scale: Scale factor for resolution
        """
        pio.write_image(
            self,
            path,
            format=format,
            width=width,
            height=height,
            scale=scale,
        )


def show_table(
    df: pd.DataFrame,
    title: str = "",
    source: Optional[str] = None,
) -> None:
    """Display a DataFrame as an interactive table.

    Args:
        df: DataFrame to display
        title: Table title
        source: Data source attribution (defaults to the configured
            ``source``; empty means no attribution footer)
    """
    backend = get_backend()
    backend.send_table(df, title=title, source=source or get_config().source)
