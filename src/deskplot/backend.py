"""Webview backend for interactive charting using pywebview.

Each chart or table opens in its own native OS window via a non-blocking
subprocess. When pywebview is not installed, deskplot falls back to opening
the same HTML in the default browser.
"""

import json
import subprocess
import sys
import tempfile
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from deskplot.config import get_config

# Try to import webview
try:
    import webview  # noqa: F401
    WEBVIEW_AVAILABLE = True
except ImportError:
    WEBVIEW_AVAILABLE = False

BACKEND: Optional["Backend"] = None

# Neutral dark toolbar surfaces. Deliberately constants rather than Config
# fields — a fork that re-themes the toolbar edits one place.
TOOLBAR_SURFACE_BG = "#1a1a2e"
TOOLBAR_SURFACE_HOVER_BG = "#1a2030"

# html2canvas (MIT, vendored) is inlined into generated HTML so PNG export
# of the header bar works offline. See vendor/html2canvas.min.js.
_HTML2CANVAS_PATH = Path(__file__).parent / "vendor" / "html2canvas.min.js"
try:
    HTML2CANVAS_JS = _HTML2CANVAS_PATH.read_text(encoding="utf-8")
except OSError:
    # Export degrades gracefully: the export button reports an error
    # instead of compositing the header.
    HTML2CANVAS_JS = ""


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert '#rrggbb' to an rgba() string with the given alpha.

    Falls back to the default accent if the input is not a 6-digit hex color.
    """
    h = hex_color.lstrip("#")
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, IndexError):
        return f"rgba(91, 154, 255, {alpha})"
    return f"rgba({r}, {g}, {b}, {alpha})"


def _brand_header_html() -> str:
    """Build the brand text block for the window header bar."""
    cfg = get_config()
    brand_color = cfg.color_brand or cfg.color_primary
    html = f'<span style="color: {brand_color};">{cfg.brand}</span>'
    if cfg.brand_secondary:
        html += (
            f' <span style="color: #2a3a5a; text-shadow: none;">|</span>'
            f' <span style="color: {cfg.color_secondary}; text-shadow:'
            f' 0 0 8px rgba(255,255,255,0.15), 0 1px 2px rgba(0,0,0,0.5);">'
            f'{cfg.brand_secondary}</span>'
        )
    return html


def _create_chart_html(
    fig: go.Figure,
    title: str = ""
) -> str:
    """Create standalone HTML for the chart with embedded Plotly."""
    cfg = get_config()
    title = title or cfg.chart_title
    timestamp = datetime.now().strftime("%A, %B %d, %Y at %H:%M")
    timestamp_html = (
        f'<div id="timestamp-text" style="font-size: 12px; color: #888888;">'
        f'{timestamp}</div>'
        if cfg.show_header_timestamp else ''
    )
    accent_fill = _hex_to_rgba(cfg.color_accent, 0.2)
    # JSON-encoded for safe interpolation into the generated JS below
    accent_js = json.dumps(cfg.color_accent)

    # Set autosize for responsive layout (no hardcoded dimensions)
    fig_copy = go.Figure(fig)
    fig_copy.update_layout(
        autosize=True,
        margin=dict(l=60, r=60, t=30, b=80),  # Balanced margins for dual-axis charts
        title=None,  # Remove internal chart title - title is shown in header bar
        # Drawing shape styling (for trend lines, rectangles, etc.)
        newshape=dict(
            line=dict(color=cfg.color_accent, width=2),
            fillcolor=accent_fill,   # Semi-transparent fill
        ),
        # Default to unified hover mode (all traces in one tooltip)
        hovermode='x unified',
        # Spike lines styling - dashed lines from hover point TO axis
        xaxis=dict(
            showspikes=False,  # Start OFF, toggle button will turn ON
            spikecolor=cfg.color_accent,
            spikethickness=1,
            spikedash='dash',
            spikemode='toaxis',  # Extends TO the axis (not across entire plot)
        ),
        yaxis=dict(
            showspikes=False,  # Start OFF, toggle button will turn ON
            spikecolor=cfg.color_accent,
            spikethickness=1,
            spikedash='dash',
            spikemode='toaxis',  # Extends TO the axis (not across entire plot)
        ),
    )

    # Generate the full Plotly HTML
    full_plotly_html = pio.to_html(
        fig_copy,
        include_plotlyjs=True,
        full_html=True,
        div_id="plotly-chart",
        config={
            'scrollZoom': True,
            'displaylogo': False,
            'responsive': True,
            'displayModeBar': True,
            # Use modeBarButtons (not modeBarButtonsToAdd) for full control over
            # grouping. Each nested array becomes a separate visual group.
            'modeBarButtons': [
                # Group 1: Reset & Theme (theme button added via JS)
                ['resetScale2d'],
                # Group 2: Zoom/Pan tools
                ['zoomIn2d', 'zoomOut2d', 'autoScale2d', 'zoom2d', 'pan2d'],
                # Group 3: Hover & Spike tools (unified/crosshair added via JS)
                ['hoverClosestCartesian', 'hoverCompareCartesian', 'toggleSpikelines'],
                # Group 4: Drawing tools
                ['drawline', 'drawcircle', 'drawrect', 'drawopenpath', 'eraseshape'],
            ],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': cfg.export_prefix,
                'height': 1080,
                'width': 1920,
                'scale': 2
            }
        }
    )

    # Inject our custom header into the Plotly HTML
    header_html = f'''
    <script>{HTML2CANVAS_JS}</script>
    <div id="chart-header" style="
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 50px;
        background: linear-gradient(90deg, #06080e 0%, #0c1628 25%, #142a4a 50%, #0c1628 75%, #06080e 100%);
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 20px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        z-index: 10000;
        font-family: 'Segoe UI', Arial, sans-serif;
    ">
        <div style="font-size: 18px; font-weight: bold; letter-spacing: 2px; text-shadow: 0 0 12px rgba(91,154,255,0.3), 0 1px 2px rgba(0,0,0,0.5);">{_brand_header_html()}</div>
        <div style="position: absolute; left: 50%; transform: translateX(-50%);
                    max-width: 55vw; overflow: hidden; text-overflow: ellipsis;
                    white-space: nowrap;
                    font-size: 14px; color: #c0c8d8;">{title}</div>
        <div style="display: flex; align-items: center; gap: 15px;">
            {timestamp_html}
            <button id="export-btn" style="
                background: {cfg.color_primary};
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
            ">Export PNG</button>
        </div>
    </div>
    <style>
        body {{
            padding-top: 50px !important;
            background-color: #06080e !important;
            margin: 0;
            overflow: hidden;
        }}
        .plotly-graph-div {{
            width: 100% !important;
            height: calc(100vh - 100px) !important;
        }}
        .main-svg {{
            background: transparent !important;
        }}
        /* Modebar positioning - bottom center */
        .modebar {{
            position: fixed !important;
            bottom: 10px !important;
            top: auto !important;
            left: 50% !important;
            right: auto !important;
            transform: translateX(-50%) !important;
            z-index: 9999 !important;
            display: flex !important;
            flex-wrap: nowrap !important;
            white-space: nowrap !important;
            overflow: visible !important;
        }}
        .modebar-container {{
            position: fixed !important;
            bottom: 10px !important;
            top: auto !important;
            left: 50% !important;
            right: auto !important;
            transform: translateX(-50%) !important;
            display: flex !important;
            flex-wrap: nowrap !important;
            overflow: visible !important;
        }}
        .modebar-group {{
            display: flex !important;
            flex-shrink: 0 !important;
            background: {TOOLBAR_SURFACE_BG} !important;
            border: 1px solid #404040 !important;
            border-radius: 8px !important;
            padding: 4px !important;
            margin: 0 3px !important;
        }}
        .modebar-btn {{
            padding: 4px 8px !important;
        }}
        .modebar-btn:hover {{
            background-color: {TOOLBAR_SURFACE_HOVER_BG} !important;
            border-radius: 4px !important;
        }}
        .modebar-btn.active {{
            background-color: {cfg.color_accent} !important;
            border-radius: 4px !important;
        }}
        /* Make toolbar icons brighter */
        .modebar-btn path {{
            fill: #ffffff !important;
            opacity: 1 !important;
        }}
        .modebar-btn:hover path {{
            fill: {cfg.color_accent} !important;
        }}
        /* Custom crosshair lines - dashed style */
        .crosshair-line {{
            position: fixed;
            pointer-events: none;
            z-index: 9998;
        }}
        .crosshair-h {{
            height: 0;
            border-top: 1px dashed {cfg.color_accent};
            left: 0;
            right: 0;
        }}
        .crosshair-v {{
            width: 0;
            border-left: 1px dashed {cfg.color_accent};
            top: 50px;
            bottom: 50px;
        }}
    </style>
    <script>
        document.getElementById('export-btn').addEventListener('click', function() {{
            var btn = document.getElementById('export-btn');
            var modebar = document.querySelector('.modebar');
            var chartDiv = document.getElementById('plotly-chart');
            var headerDiv = document.getElementById('chart-header');

            btn.style.visibility = 'hidden';
            if (modebar) modebar.style.visibility = 'hidden';

            var scale = 2;
            var exportWidth = window.innerWidth;
            var headerHeight = headerDiv ? headerDiv.offsetHeight : 50;
            var chartHeight = window.innerHeight - headerHeight;

            // Use Plotly.toImage for the chart (handles WebGL/3D properly)
            Plotly.toImage(chartDiv, {{
                format: 'png',
                width: exportWidth,
                height: chartHeight,
                scale: scale
            }}).then(function(chartDataUrl) {{
                // Now capture just the header with html2canvas
                return html2canvas(headerDiv, {{
                    backgroundColor: null,
                    scale: scale,
                    useCORS: true,
                    logging: false
                }}).then(function(headerCanvas) {{
                    // Load chart image
                    var chartImg = new Image();
                    chartImg.onload = function() {{
                        // Composite: header on top, chart below
                        var finalCanvas = document.createElement('canvas');
                        finalCanvas.width = exportWidth * scale;
                        finalCanvas.height = (headerHeight + chartHeight) * scale;
                        var ctx = finalCanvas.getContext('2d');

                        // Black background
                        ctx.fillStyle = '#06080e';
                        ctx.fillRect(0, 0, finalCanvas.width, finalCanvas.height);

                        // Draw header
                        ctx.drawImage(headerCanvas, 0, 0, headerCanvas.width, headerCanvas.height,
                                      0, 0, finalCanvas.width, headerHeight * scale);

                        // Draw chart below header
                        ctx.drawImage(chartImg, 0, 0, chartImg.width, chartImg.height,
                                      0, headerHeight * scale, finalCanvas.width, chartHeight * scale);

                        var dataUrl = finalCanvas.toDataURL('image/png');

                        btn.style.visibility = 'visible';
                        if (modebar) modebar.style.visibility = 'visible';

                        if (window.pywebview && window.pywebview.api) {{
                            window.pywebview.api.save_image(dataUrl).then(function(result) {{
                                if (result.success) {{
                                    btn.textContent = 'Saved!';
                                    setTimeout(function() {{ btn.textContent = 'Export PNG'; btn.disabled = false; }}, 2000);
                                }} else {{
                                    btn.textContent = 'Error';
                                    console.error(result.error);
                                    setTimeout(function() {{ btn.textContent = 'Export PNG'; btn.disabled = false; }}, 2000);
                                }}
                            }});
                        }} else {{
                            var link = document.createElement('a');
                            link.download = {json.dumps(cfg.export_prefix)} + '_' + new Date().toISOString().slice(0,19).replace(/[:-]/g, '') + '.png';
                            link.href = dataUrl;
                            link.click();
                            btn.textContent = 'Export PNG';
                            btn.disabled = false;
                        }}
                    }};
                    chartImg.src = chartDataUrl;
                }});
            }}).catch(function(err) {{
                btn.style.visibility = 'visible';
                if (modebar) modebar.style.visibility = 'visible';
                console.error('Export failed:', err);
                btn.textContent = 'Error';
                setTimeout(function() {{ btn.textContent = 'Export PNG'; btn.disabled = false; }}, 2000);
            }});
        }});

        // Responsive resize handler
        function resizeChart() {{
            var chartDiv = document.getElementById('plotly-chart');
            if (chartDiv && typeof Plotly !== 'undefined') {{
                Plotly.relayout(chartDiv, {{
                    width: window.innerWidth,
                    height: window.innerHeight - 100  // Account for header (50px) and toolbar space (50px)
                }});
            }}
        }}

        // Handle window resize events
        window.addEventListener('resize', resizeChart);

        // Initial resize on load
        window.addEventListener('load', function() {{
            setTimeout(resizeChart, 100);
        }});

        // Custom crosshair functionality (dashed lines across entire chart)
        var crosshairEnabled = false;
        var crosshairH = null;
        var crosshairV = null;

        function createCrosshair() {{
            if (crosshairH) return;  // Already created

            // Create horizontal line (spans full width)
            crosshairH = document.createElement('div');
            crosshairH.className = 'crosshair-line crosshair-h';
            crosshairH.style.display = 'none';
            document.body.appendChild(crosshairH);

            // Create vertical line (spans chart height)
            crosshairV = document.createElement('div');
            crosshairV.className = 'crosshair-line crosshair-v';
            crosshairV.style.display = 'none';
            document.body.appendChild(crosshairV);

            // Track mouse movement on the entire document
            document.addEventListener('mousemove', function(e) {{
                if (!crosshairEnabled) return;

                // Only show when mouse is in chart area (below header, above toolbar)
                if (e.clientY > 50 && e.clientY < window.innerHeight - 50) {{
                    crosshairH.style.display = 'block';
                    crosshairH.style.top = e.clientY + 'px';
                    crosshairV.style.display = 'block';
                    crosshairV.style.left = e.clientX + 'px';
                }} else {{
                    crosshairH.style.display = 'none';
                    crosshairV.style.display = 'none';
                }}
            }});

            document.addEventListener('mouseleave', function() {{
                if (crosshairH) crosshairH.style.display = 'none';
                if (crosshairV) crosshairV.style.display = 'none';
            }});
        }}

        function setCrosshairEnabled(enabled) {{
            crosshairEnabled = enabled;
            if (!enabled) {{
                if (crosshairH) crosshairH.style.display = 'none';
                if (crosshairV) crosshairV.style.display = 'none';
            }}
        }}

        function setCrosshairColor(color) {{
            if (crosshairH) crosshairH.style.borderTopColor = color;
            if (crosshairV) crosshairV.style.borderLeftColor = color;
        }}

        // Theme toggle functionality
        var isDarkTheme = true;

        function toggleTheme() {{
            var chartDiv = document.getElementById('plotly-chart');
            var layout = chartDiv._fullLayout;
            var plotlyDiv = document.querySelector('.plotly-graph-div');
            var svgContainer = document.querySelector('.svg-container');
            var mainSvg = document.querySelector('.main-svg');
            var themeBtn = document.getElementById('theme-toggle-btn');

            isDarkTheme = !isDarkTheme;

            // Build update object using DOT NOTATION to preserve axis properties
            // Using object syntax (xaxis: {{}}) would REPLACE the entire axis config
            // Dot notation (xaxis.gridcolor) only updates that specific property
            var update = {{}};

            if (isDarkTheme) {{
                // Dark theme colors
                update['paper_bgcolor'] = '#06080e';
                update['plot_bgcolor'] = '#06080e';
                update['font.color'] = '#6b7080';
                update['legend.bgcolor'] = 'rgba(0,0,0,0)';

                // Dynamically find and update ALL axes (xaxis, xaxis2, yaxis, yaxis2, etc.)
                Object.keys(layout).forEach(function(key) {{
                    if (key.match(/^xaxis\\d*$/)) {{
                        update[key + '.gridcolor'] = 'rgba(255,255,255,0.05)';
                        update[key + '.gridwidth'] = 0.5;
                        update[key + '.griddash'] = 'dot';
                        update[key + '.showline'] = false;
                        update[key + '.tickfont.color'] = '#6b7080';
                        update[key + '.title.font.color'] = '#6b7080';
                        update[key + '.spikecolor'] = {accent_js};
                        update[key + '.zerolinecolor'] = 'rgba(255,255,255,0.08)';
                        update[key + '.showspikes'] = false;
                    }}
                    if (key.match(/^yaxis\\d*$/)) {{
                        update[key + '.gridcolor'] = 'rgba(255,255,255,0.05)';
                        update[key + '.gridwidth'] = 0.5;
                        update[key + '.griddash'] = 'dot';
                        update[key + '.showline'] = false;
                        update[key + '.tickfont.color'] = '#6b7080';
                        update[key + '.title.font.color'] = '#6b7080';
                        update[key + '.spikecolor'] = {accent_js};
                        update[key + '.zerolinecolor'] = 'rgba(255,255,255,0.08)';
                        update[key + '.showspikes'] = false;
                    }}
                }});

                // Update button icon to sun (indicating click will switch to light)
                if (themeBtn) themeBtn.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18"><circle cx="12" cy="12" r="5" fill="white"/><g stroke="white" stroke-width="2"><line x1="12" y1="1" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="6.34" y2="6.34"/><line x1="17.66" y1="17.66" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="6.34" y2="17.66"/><line x1="17.66" y1="6.34" x2="19.78" y2="4.22"/></g></svg>';

                // Update DOM backgrounds
                document.body.style.setProperty('background-color', '#06080e', 'important');
                if (plotlyDiv) plotlyDiv.style.setProperty('background-color', '#06080e', 'important');
                if (svgContainer) svgContainer.style.setProperty('background-color', '#06080e', 'important');
                if (mainSvg) mainSvg.style.setProperty('background', '#06080e', 'important');

                setCrosshairColor({accent_js});
            }} else {{
                // Light theme colors
                update['paper_bgcolor'] = '#ffffff';
                update['plot_bgcolor'] = '#f8f9fa';
                update['font.color'] = '#333333';
                update['legend.bgcolor'] = 'rgba(255, 255, 255, 0.5)';

                // Dynamically find and update ALL axes
                Object.keys(layout).forEach(function(key) {{
                    if (key.match(/^xaxis\\d*$/)) {{
                        update[key + '.gridcolor'] = '#e0e0e0';
                        update[key + '.gridwidth'] = 0.5;
                        update[key + '.griddash'] = 'dot';
                        update[key + '.linecolor'] = '#333333';
                        update[key + '.tickcolor'] = '#333333';
                        update[key + '.tickfont.color'] = '#333333';
                        update[key + '.title.font.color'] = '#333333';
                        update[key + '.spikecolor'] = '#0066cc';
                        update[key + '.zerolinecolor'] = '#666666';
                        update[key + '.showspikes'] = false;
                    }}
                    if (key.match(/^yaxis\\d*$/)) {{
                        update[key + '.gridcolor'] = '#e0e0e0';
                        update[key + '.gridwidth'] = 0.5;
                        update[key + '.griddash'] = 'dot';
                        update[key + '.linecolor'] = '#333333';
                        update[key + '.tickcolor'] = '#333333';
                        update[key + '.tickfont.color'] = '#333333';
                        update[key + '.title.font.color'] = '#333333';
                        update[key + '.spikecolor'] = '#0066cc';
                        update[key + '.zerolinecolor'] = '#666666';
                        update[key + '.showspikes'] = false;
                    }}
                }});

                // Update button icon to moon (indicating click will switch to dark)
                if (themeBtn) themeBtn.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" fill="white"/></svg>';

                // Update DOM backgrounds
                document.body.style.setProperty('background-color', '#ffffff', 'important');
                if (plotlyDiv) plotlyDiv.style.setProperty('background-color', '#ffffff', 'important');
                if (svgContainer) svgContainer.style.setProperty('background-color', '#ffffff', 'important');
                if (mainSvg) mainSvg.style.setProperty('background', '#ffffff', 'important');

                setCrosshairColor('#0066cc');
            }}

            // Apply the update - dot notation preserves all other axis properties
            Plotly.relayout(chartDiv, update);
        }}

        // Set unified hover mode (all traces in one tooltip)
        function setUnifiedHover() {{
            var chartDiv = document.getElementById('plotly-chart');
            var unifiedBtn = document.getElementById('unified-hover-btn');
            Plotly.relayout(chartDiv, {{ hovermode: 'x unified' }});
            // Set this button as active
            if (unifiedBtn) unifiedBtn.classList.add('active');
            // Note: Crosshair is independent - controlled by its own button
        }}

        // Add custom buttons to modebar after page loads
        window.addEventListener('load', function() {{
            setTimeout(function() {{
                var modebarGroups = document.querySelectorAll('.modebar-group');

                // Add "Unified" button to the hover/spike group (third group, index 2)
                if (modebarGroups.length > 2) {{
                    var hoverGroup = modebarGroups[2];
                    var unifiedBtn = document.createElement('a');
                    unifiedBtn.id = 'unified-hover-btn';
                    unifiedBtn.className = 'modebar-btn active';  // Active by default since unified is default mode
                    unifiedBtn.setAttribute('data-title', 'Unified Tooltip (All Traces)');
                    unifiedBtn.style.cssText = 'cursor: pointer; padding: 4px 8px !important; display: flex; align-items: center;';
                    // Icon: stacked lines representing unified tooltip
                    unifiedBtn.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18"><rect x="3" y="4" width="18" height="16" rx="2" fill="none" stroke="white" stroke-width="2"/><line x1="7" y1="9" x2="17" y2="9" stroke="white" stroke-width="2"/><line x1="7" y1="13" x2="17" y2="13" stroke="white" stroke-width="2"/><line x1="7" y1="17" x2="13" y2="17" stroke="white" stroke-width="2"/></svg>';
                    unifiedBtn.onclick = setUnifiedHover;
                    // Insert at the beginning of the hover group
                    hoverGroup.insertBefore(unifiedBtn, hoverGroup.firstChild);

                    // When other hover buttons are clicked, remove active from unified button
                    var otherHoverBtns = hoverGroup.querySelectorAll('.modebar-btn:not(#unified-hover-btn)');
                    otherHoverBtns.forEach(function(btn) {{
                        btn.addEventListener('click', function() {{
                            unifiedBtn.classList.remove('active');
                        }});
                    }});

                    // Custom Crosshair button (mutually exclusive with spike lines)
                    var crosshairBtn = document.createElement('a');
                    crosshairBtn.id = 'crosshair-btn';
                    crosshairBtn.className = 'modebar-btn';
                    crosshairBtn.setAttribute('data-title', 'Toggle Crosshair');
                    crosshairBtn.style.cssText = 'cursor: pointer; padding: 4px 8px !important; display: flex; align-items: center;';
                    // Icon: crosshair (plus sign in circle)
                    crosshairBtn.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18"><circle cx="12" cy="12" r="9" fill="none" stroke="white" stroke-width="2"/><line x1="12" y1="3" x2="12" y2="21" stroke="white" stroke-width="2"/><line x1="3" y1="12" x2="21" y2="12" stroke="white" stroke-width="2"/></svg>';
                    hoverGroup.appendChild(crosshairBtn);

                    // Get native spike lines button and hook into it for mutual exclusivity
                    var spikeBtn = hoverGroup.querySelector('[data-title="Toggle Spike Lines"]');
                    var spikesEnabled = false;

                    if (spikeBtn) {{
                        spikeBtn.addEventListener('click', function() {{
                            // Check state after Plotly processes the click
                            setTimeout(function() {{
                                var chartDiv = document.getElementById('plotly-chart');
                                var xaxis = chartDiv._fullLayout.xaxis;
                                spikesEnabled = xaxis && xaxis.showspikes;

                                if (spikesEnabled) {{
                                    // Spike lines turned ON - set closest hover mode
                                    Plotly.relayout(chartDiv, {{ hovermode: 'closest' }});
                                    unifiedBtn.classList.remove('active');
                                    // Turn OFF crosshair (mutually exclusive)
                                    crosshairEnabled = false;
                                    crosshairBtn.classList.remove('active');
                                    if (crosshairH) crosshairH.style.display = 'none';
                                    if (crosshairV) crosshairV.style.display = 'none';
                                }}
                            }}, 50);
                        }});
                    }}

                    // Crosshair click handler - mutually exclusive with spike lines
                    crosshairBtn.onclick = function() {{
                        crosshairEnabled = !crosshairEnabled;
                        var chartDiv = document.getElementById('plotly-chart');
                        if (crosshairEnabled) {{
                            crosshairBtn.classList.add('active');
                            // Turn OFF spike lines (mutually exclusive) - click the native button if spikes are on
                            if (spikesEnabled && spikeBtn) {{
                                spikeBtn.click();
                                spikesEnabled = false;
                            }}
                        }} else {{
                            crosshairBtn.classList.remove('active');
                            if (crosshairH) crosshairH.style.display = 'none';
                            if (crosshairV) crosshairV.style.display = 'none';
                        }}
                    }};

                    // Create crosshair elements
                    createCrosshair();
                }}

                // Add theme toggle button to the first group (with reset)
                var resetGroup = modebarGroups[0];
                if (resetGroup) {{
                    var themeBtn = document.createElement('a');
                    themeBtn.id = 'theme-toggle-btn';
                    themeBtn.className = 'modebar-btn';
                    themeBtn.setAttribute('data-title', 'Toggle Theme');
                    themeBtn.style.cssText = 'cursor: pointer; padding: 4px 8px !important; display: flex; align-items: center;';
                    themeBtn.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18"><circle cx="12" cy="12" r="5" fill="white"/><g stroke="white" stroke-width="2"><line x1="12" y1="1" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="6.34" y2="6.34"/><line x1="17.66" y1="17.66" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="6.34" y2="17.66"/><line x1="17.66" y1="6.34" x2="19.78" y2="4.22"/></g></svg>';
                    themeBtn.onclick = toggleTheme;
                    resetGroup.appendChild(themeBtn);
                }}
            }}, 200);
        }});
    </script>
    '''

    # Insert header right after <body> tag
    html = full_plotly_html.replace('<body>', f'<body>{header_html}')

    return html


def _create_table_html(
    df: pd.DataFrame,
    title: str = "",
    source: str = ""
) -> str:
    """Create standalone HTML for a data table."""
    cfg = get_config()
    title = title or cfg.table_title
    source = source or cfg.source
    source_html = f'<div class="source">Source: {source}</div>' if source else ''
    timestamp = datetime.now().strftime("%A, %B %d, %Y at %H:%M")
    timestamp_html = (
        f'<div class="timestamp">{timestamp}</div>'
        if cfg.show_header_timestamp else ''
    )
    # Escape "</" so cell content like "</script>" cannot terminate the
    # script block the data is embedded in.
    json_data = df.to_json(orient="split", date_format="iso").replace("</", "<\\/")
    # JSON-encode the download filename so quotes in the title cannot break
    # the surrounding JS string literal.
    csv_filename = json.dumps(f'{title.replace(" ", "_")}.csv')
    # Signed-value styles, JSON-encoded for safe interpolation into JS
    value_up_style = json.dumps(f"color: {cfg.color_value_up};")
    value_down_style = json.dumps(f"color: {cfg.color_value_down};")

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{ width: 100%; height: 100%; background-color: #06080e; overflow: hidden; }}
        #header {{
            position: relative;
            height: 50px;
            background: linear-gradient(90deg, #06080e 0%, #0c1628 25%, #142a4a 50%, #0c1628 75%, #06080e 100%);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 20px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }}
        .logo-text {{
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 18px;
            font-weight: bold;
            color: {cfg.color_brand or cfg.color_primary};
            letter-spacing: 2px;
        }}
        .title {{
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            max-width: 55vw;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 14px;
            color: #ffffff;
        }}
        .header-right {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        .timestamp {{
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 12px;
            color: #888888;
        }}
        .export-btn {{
            background: {cfg.color_primary};
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 12px;
        }}
        .export-btn:hover {{ filter: brightness(0.9); }}
        #table-container {{
            height: calc(100% - 100px);
            overflow: auto;
            padding: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 13px;
            color: white;
        }}
        th, td {{
            padding: 10px 15px;
            text-align: left;
            border-bottom: 1px solid #333;
        }}
        th {{
            background-color: #1e1e1e;
            font-weight: bold;
            position: sticky;
            top: 0;
            cursor: pointer;
        }}
        th:hover {{ background-color: #333; }}
        tr:nth-child(odd) {{ background-color: #242424; }}
        tr:nth-child(even) {{ background-color: #333333; }}
        tr:hover {{ background-color: #444 !important; }}
        #footer {{
            height: 50px;
            background-color: #1a1a2e;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 20px;
            border-top: 1px solid rgba(255,255,255,0.08);
        }}
        .source {{
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 11px;
            color: #888;
        }}
    </style>
</head>
<body>
    <div id="header">
        <div class="logo-text">{cfg.brand}</div>
        <div class="title">{title}</div>
        <div class="header-right">
            {timestamp_html}
            <button class="export-btn" onclick="exportCSV()">Export CSV</button>
        </div>
    </div>
    <div id="table-container">
        <table id="dataTable">
            <thead id="tableHead"></thead>
            <tbody id="tableBody"></tbody>
        </table>
    </div>
    <div id="footer">
        {source_html}
    </div>
    <script>
        var tableData = {json_data};
        var sortCol = -1;
        var sortAsc = true;

        function renderTable() {{
            var thead = document.getElementById('tableHead');
            var tbody = document.getElementById('tableBody');

            var headerHtml = '<tr>';
            tableData.columns.forEach(function(col, idx) {{
                var arrow = sortCol === idx ? (sortAsc ? ' ▲' : ' ▼') : '';
                headerHtml += '<th onclick="sortBy(' + idx + ')">' + col + arrow + '</th>';
            }});
            headerHtml += '</tr>';
            thead.innerHTML = headerHtml;

            var bodyHtml = '';
            tableData.data.forEach(function(row) {{
                bodyHtml += '<tr>';
                row.forEach(function(cell) {{
                    var val = cell === null ? '' : cell;
                    var style = '';
                    if (typeof cell === 'number') {{
                        style = cell < 0 ? {value_down_style} : cell > 0 ? {value_up_style} : '';
                    }}
                    bodyHtml += '<td style="' + style + '">' + val + '</td>';
                }});
                bodyHtml += '</tr>';
            }});
            tbody.innerHTML = bodyHtml;
        }}

        function sortBy(colIdx) {{
            if (sortCol === colIdx) {{ sortAsc = !sortAsc; }}
            else {{ sortCol = colIdx; sortAsc = true; }}
            tableData.data.sort(function(a, b) {{
                var valA = a[colIdx], valB = b[colIdx];
                if (valA === null) return 1;
                if (valB === null) return -1;
                if (typeof valA === 'number' && typeof valB === 'number') {{
                    return sortAsc ? valA - valB : valB - valA;
                }}
                var strA = String(valA).toLowerCase(), strB = String(valB).toLowerCase();
                return sortAsc ? (strA < strB ? -1 : strA > strB ? 1 : 0) : (strA > strB ? -1 : strA < strB ? 1 : 0);
            }});
            renderTable();
        }}

        function exportCSV() {{
            var csv = tableData.columns.join(',') + '\\n';
            tableData.data.forEach(function(row) {{
                csv += row.map(function(cell) {{
                    if (cell === null) return '';
                    var str = String(cell);
                    return str.includes(',') ? '"' + str + '"' : str;
                }}).join(',') + '\\n';
            }});
            var blob = new Blob([csv], {{ type: 'text/csv' }});
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = {csv_filename};
            a.click();
        }}

        renderTable();
    </script>
</body>
</html>'''
    return html


# Viewer script that runs in a subprocess
VIEWER_SCRIPT = '''
import sys
import os
import base64
import webview
from datetime import datetime

class Api:
    def save_image(self, data_url):
        """Save base64 image data to Downloads folder."""
        try:
            # Extract base64 data
            header, encoded = data_url.split(",", 1)
            data = base64.b64decode(encoded)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}.png"

            # Save to Downloads
            downloads_path = os.path.expanduser("~/Downloads")
            filepath = os.path.join(downloads_path, filename)

            with open(filepath, "wb") as f:
                f.write(data)

            return {"success": True, "path": filepath}
        except Exception as e:
            return {"success": False, "error": str(e)}

html_path = sys.argv[1]
title = sys.argv[2] if len(sys.argv) > 2 else "Chart"
width = int(sys.argv[3]) if len(sys.argv) > 3 else 1400
height = int(sys.argv[4]) if len(sys.argv) > 4 else 800
prefix = sys.argv[5] if len(sys.argv) > 5 else "chart"

api = Api()

window = webview.create_window(
    title,
    html_path,
    width=width,
    height=height,
    background_color='#06080e',
    js_api=api
)

webview.start()
'''


class Backend:
    """Webview backend for interactive charts.

    Displays interactive Plotly charts in native windows using pywebview.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the backend."""
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.WIDTH = 1400
        self.HEIGHT = 800

        log_prefix = get_config().log_prefix
        if WEBVIEW_AVAILABLE:
            print(f"{log_prefix} pywebview backend ready - native windows enabled")
        else:
            for line in (
                "=" * 62,
                "WARNING: pywebview is unavailable - charts will open in",
                "BROWSER TABS instead of native desktop windows.",
                "Native windows are deskplot's intended experience; the",
                "browser is only a fallback for headless/SSH sessions or a",
                "missing OS webview. To fix: pip install pywebview",
                "(on Linux also install its GTK or Qt system packages:",
                "https://pywebview.flowrl.com/guide/installation.html)",
                "=" * 62,
            ):
                print(f"{log_prefix} {line}")

        self._initialized = True

    def send_figure(
        self,
        fig: go.Figure,
        title: str = "",
        **kwargs
    ):
        """Display a Plotly figure in a native window.

        Args:
            fig: Plotly figure to display
            title: Window title
        """
        import re
        clean_title = (
            re.sub(r"<[^>]*>", "", title) if title else get_config().chart_title
        )

        if WEBVIEW_AVAILABLE:
            self._show_in_webview(fig, clean_title)
        else:
            self._show_in_browser(fig, clean_title)

    def send_table(
        self,
        df: pd.DataFrame,
        title: str = "",
        source: str = "",
        **kwargs
    ):
        """Display a DataFrame as an interactive table in a native window.

        Args:
            df: DataFrame to display
            title: Window title
            source: Data source attribution
        """
        import re
        cfg = get_config()
        source = source or cfg.source
        clean_title = re.sub(r"<[^>]*>", "", title) if title else cfg.table_title

        if WEBVIEW_AVAILABLE:
            self._show_table_in_webview(df, clean_title, source)
        else:
            self._show_table_in_browser(df, clean_title, source)

    def _launch_viewer(self, temp_path: str, title: str):
        """Launch the pywebview viewer subprocess (non-blocking)."""
        cfg = get_config()

        # Write viewer script to temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            prefix='chart_viewer_'
        ) as f:
            f.write(VIEWER_SCRIPT)
            viewer_path = f.name

        window_title = cfg.window_title_format.format(brand=cfg.brand, title=title)
        subprocess.Popen(
            [sys.executable, viewer_path, temp_path, window_title,
             str(self.WIDTH), str(self.HEIGHT), cfg.export_prefix],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @staticmethod
    def _write_temp_html(html: str) -> str:
        """Write HTML to a temp file (not auto-deleted) and return its path."""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.html',
            delete=False,
            prefix='chart_',
            encoding='utf-8'
        ) as f:
            f.write(html)
            return f.name

    def _show_in_webview(self, fig: go.Figure, title: str):
        """Show figure in a pywebview native window via subprocess."""
        html = _create_chart_html(fig, title)
        temp_path = self._write_temp_html(html)
        self._launch_viewer(temp_path, title)

    def _show_table_in_webview(self, df: pd.DataFrame, title: str, source: str):
        """Show table in a pywebview native window via subprocess."""
        html = _create_table_html(df, title, source)
        temp_path = self._write_temp_html(html)
        self._launch_viewer(temp_path, title)

    def _show_in_browser(self, fig: go.Figure, title: str):
        """Fallback: show figure in browser."""
        html = _create_chart_html(fig, title)
        temp_path = self._write_temp_html(html)
        webbrowser.open(Path(temp_path).as_uri())

    def _show_table_in_browser(self, df: pd.DataFrame, title: str, source: str):
        """Fallback: show table in browser."""
        html = _create_table_html(df, title, source)
        temp_path = self._write_temp_html(html)
        webbrowser.open(Path(temp_path).as_uri())


def create_backend() -> Backend:
    """Create or get the backend singleton."""
    global BACKEND
    if BACKEND is None:
        BACKEND = Backend()
    return BACKEND


def get_backend() -> Backend:
    """Get the backend singleton."""
    global BACKEND
    if BACKEND is None:
        BACKEND = Backend()
    return BACKEND
