import os
import plotly.graph_objects as go
import plotly.io as pio
from typing import Optional


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

    prices_sek = [p['kWh_SEK'] for p in prices]
    min_p, max_p = min(prices_sek), max(prices_sek)
    span = max_p - min_p or 1.0  # avoid division by zero when all prices equal

    normalized = [(p - min_p) / span for p in prices_sek]
    colors = [f'rgb({int(255 * n)}, 0, {int(255 * (1 - n))})' for n in normalized]

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
