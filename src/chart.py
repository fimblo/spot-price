import os
import plotly.graph_objects as go
import plotly.io as pio
from typing import Optional

# (threshold in öre, hex colour)
_COLOR_THRESHOLDS = [
    (30,  '#27ae60'),   # green      — dirt cheap
    (70,  '#a8d86e'),   # light green — cheap
    (100, '#f1c40f'),   # yellow     — acceptable
    (130, '#e67e22'),   # orange     — expensive
]
_COLOR_PAINFUL = '#e74c3c'   # red

# Chart chrome per report — lets a day (morning) and night (evening) chart be
# told apart at a glance even as a bare thumbnail. Surface/ink values are the
# validated light/dark tokens from the dataviz skill's reference palette.
#
# anchor_*  — the vertical time-reference line (see _ANCHOR_HHMM). Dark-on-light
#             at 0.55 reads the same as light-on-dark at 0.85: a thin light line
#             loses more to antialiasing when Telegram downscales the PNG, so the
#             night value is deliberately not a straight mirror of the day one.
# mark_*    — peak/trough label ink. The bar palette above is tuned for a light
#             ground, so the night theme lifts both toward the light end rather
#             than reusing #e74c3c/#27ae60, which go muddy on #1a1a19.
_THEMES = {
    'day': {
        'paper_bgcolor': '#fcfcfb',
        'plot_bgcolor':  '#fcfcfb',
        'ink':           '#0b0b0b',
        'gridcolor':     '#e1e0d9',
        'linecolor':     '#c3c2b7',
        'anchor':        '#0b0b0b',
        'anchor_alpha':  0.55,
        'mark_high':     '#e74c3c',
        'mark_low':      '#27ae60',
    },
    'night': {
        'paper_bgcolor': '#1a1a19',
        'plot_bgcolor':  '#1a1a19',
        'ink':           '#ffffff',
        'gridcolor':     '#2c2c2a',
        'linecolor':     '#383835',
        'anchor':        '#9ec9ff',
        'anchor_alpha':  0.85,
        'mark_high':     '#ff6b5a',
        'mark_low':      '#5fd68a',
    },
}

# The time the vertical reference line marks, per theme. The morning chart runs
# through the day, so noon splits it; the evening chart straddles two dates, so
# midnight is the useful landmark — it is also the only visual cue that the
# chart has crossed into tomorrow.
_ANCHOR_HHMM = {'day': '12:00', 'night': '00:00'}

# Headroom above the tallest bar, so the top-aligned peak/trough labels have
# somewhere to sit without colliding with the data.
_HEADROOM = 1.18

# Two labels closer together than this fraction of the series would overlap;
# the lower-priced one drops a line when they do.
_CROWDED_FRACTION = 0.18


def price_color(price_sek: float) -> str:
    """Return a hex bar colour for a price in SEK/kWh based on fixed öre thresholds."""
    ore = price_sek * 100
    for threshold, color in _COLOR_THRESHOLDS:
        if ore < threshold:
            return color
    return _COLOR_PAINFUL


def _anchor_timestamp(prices: list[dict], theme: str) -> Optional[str]:
    """
    Return the ISO timestamp of the theme's reference time, or None when the
    chart does not span it (e.g. a morning report generated after noon).
    """
    hhmm = _ANCHOR_HHMM[theme]
    for p in prices:
        if p['time_start'][11:16] == hhmm:
            return p['time_start']
    return None


def generate_price_chart(
    prices: list[dict],
    date_str: str,
    region: str,
    output_dir: str = 'output',
    theme: str = 'day',
) -> Optional[str]:
    """
    Generate a colour-coded bar chart of hourly spot prices.

    Bars are coloured by absolute price thresholds (see price_color). Two extra
    cues make the chart readable as a Telegram thumbnail, without opening and
    zooming the image: a thin dotted vertical line at noon (day) or midnight
    (night) to orient the reader in the timeline, and labels naming the times of
    the most and least expensive slots, aligned along the top of the plot.

    Args:
        prices:     list of dicts with 'time_start' (ISO string) and 'kWh_SEK' (float)
        date_str:   YYYY-MM-DD, used in title and filename
        region:     region code, used in title and filename
        output_dir: directory to write the PNG; created if missing
        theme:      'day' (light chrome) or 'night' (dark chrome) — lets the
                    morning and evening reports be told apart at a glance

    Returns:
        Absolute path to the generated PNG, or None when prices is empty.
    """
    if not prices:
        return None

    os.makedirs(output_dir, exist_ok=True)

    colors = [price_color(p['kWh_SEK']) for p in prices]
    chrome = _THEMES[theme]
    ore = [p['kWh_SEK'] * 100 for p in prices]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[p['time_start'] for p in prices],
        y=ore,   # SEK → öre for readability
        marker_color=colors,
        name='Spot Price',
    ))
    fig.update_layout(
        title=f'Spot Prices {date_str} — {region}',
        xaxis_title='Hour',
        yaxis_title='öre / kWh',
        xaxis=dict(dtick=3600000, tickformat='%H'),
        yaxis=dict(range=[0, max(ore) * _HEADROOM]),
        paper_bgcolor=chrome['paper_bgcolor'],
        plot_bgcolor=chrome['plot_bgcolor'],
        font_color=chrome['ink'],
    )
    fig.update_xaxes(gridcolor=chrome['gridcolor'], linecolor=chrome['linecolor'])
    fig.update_yaxes(gridcolor=chrome['gridcolor'], linecolor=chrome['linecolor'])

    anchor = _anchor_timestamp(prices, theme)
    if anchor is not None:
        fig.add_vline(
            x=anchor,
            line_width=2,
            line_dash='dot',
            line_color=chrome['anchor'],
            opacity=chrome['anchor_alpha'],
        )

    idx_high = max(range(len(prices)), key=lambda i: prices[i]['kWh_SEK'])
    idx_low = min(range(len(prices)), key=lambda i: prices[i]['kWh_SEK'])
    crowded = abs(idx_high - idx_low) < len(prices) * _CROWDED_FRACTION

    for idx, glyph, color, yshift in (
        (idx_high, '▲', chrome['mark_high'], -6),
        (idx_low,  '▼', chrome['mark_low'], -26 if crowded else -6),
    ):
        fig.add_annotation(
            x=prices[idx]['time_start'],
            y=1, yref='paper', yanchor='top', yshift=yshift,
            text=f"{glyph} {prices[idx]['time_start'][11:16]}",
            showarrow=False,
            font=dict(size=15, color=color),
        )

    output_path = os.path.join(output_dir, f'spot-price-{date_str}-{region}.png')
    pio.write_image(fig, output_path, format='png')
    return output_path
