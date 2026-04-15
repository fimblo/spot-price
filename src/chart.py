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


def price_color(price_sek: float) -> str:
    """Return a hex bar colour for a price in SEK/kWh based on fixed öre thresholds."""
    ore = price_sek * 100
    for threshold, color in _COLOR_THRESHOLDS:
        if ore < threshold:
            return color
    return _COLOR_PAINFUL


def generate_price_chart(
    prices: list[dict],
    date_str: str,
    region: str,
    output_dir: str = 'output',
) -> Optional[str]:
    """
    Generate a colour-coded bar chart of hourly spot prices.

    Bars are coloured blue (cheap) → red (expensive) based on normalised price.

    Args:
        prices:     list of dicts with 'time_start' (ISO string) and 'kWh_SEK' (float)
        date_str:   YYYY-MM-DD, used in title and filename
        region:     region code, used in title and filename
        output_dir: directory to write the PNG; created if missing

    Returns:
        Absolute path to the generated PNG, or None when prices is empty.
    """
    if not prices:
        return None

    os.makedirs(output_dir, exist_ok=True)

    colors = [price_color(p['kWh_SEK']) for p in prices]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[p['time_start'] for p in prices],
        y=[p['kWh_SEK'] * 100 for p in prices],   # SEK → öre for readability
        marker_color=colors,
        name='Spot Price',
    ))
    fig.update_layout(
        title=f'Spot Prices {date_str} — {region}',
        xaxis_title='Hour',
        yaxis_title='öre / kWh',
        xaxis=dict(dtick=3600000, tickformat='%H'),
    )

    output_path = os.path.join(output_dir, f'spot-price-{date_str}-{region}.png')
    pio.write_image(fig, output_path, format='png')
    return output_path
