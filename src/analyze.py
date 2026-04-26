from datetime import datetime, timedelta
from typing import Optional

# (threshold in öre, label)
_PRICE_THRESHOLDS = [
    (30,  'dirt cheap'),
    (70,  'cheap'),
    (100, 'acceptable'),
    (130, 'expensive'),
]


def price_label(price_sek: float) -> str:
    """Return a human label for a price in SEK/kWh based on fixed öre thresholds."""
    ore = price_sek * 100
    for threshold, label in _PRICE_THRESHOLDS:
        if ore < threshold:
            return label
    return 'painful'


def find_cheapest_window(prices: list[dict], window_hours: float = 1.5) -> Optional[dict]:
    """
    Find the cheapest time window of given duration in a list of hourly prices.

    For a 1.5h window starting at index i:
        cost   = price[i] * 1.0 + price[i+1] * 0.5
        avg    = cost / 1.5

    Args:
        prices: list of dicts with 'time_start' (ISO string) and 'kWh_SEK' (float)
        window_hours: duration in hours (default 1.5)

    Returns:
        dict with 'start' (datetime), 'end' (datetime), 'avg_price' (float/kWh_SEK)
        or None if there is insufficient data for even one window.
    """
    if not prices:
        return None

    sorted_prices = sorted(prices, key=lambda p: p['time_start'])
    n = len(sorted_prices)

    full_hours = int(window_hours)
    partial = window_hours - full_hours
    hours_needed = full_hours + (1 if partial > 0 else 0)

    if n < hours_needed:
        return None

    best: Optional[dict] = None

    for i in range(n - hours_needed + 1):
        cost = sum(sorted_prices[i + j]['kWh_SEK'] for j in range(full_hours))
        weight = float(full_hours)

        if partial > 0:
            cost += sorted_prices[i + full_hours]['kWh_SEK'] * partial
            weight += partial

        avg = cost / weight

        if best is None or avg < best['avg_price']:
            start_dt = datetime.fromisoformat(sorted_prices[i]['time_start'])
            best = {
                'start': start_dt,
                'end': start_dt + timedelta(hours=window_hours),
                'avg_price': avg,
            }

    return best


def find_cheap_start_span(prices: list[dict], window_hours: float = 1.5) -> Optional[dict]:
    """
    Find the cheapest N-hour window plus the contiguous span of start times
    whose N-hour window average lands in the same price zone (price_label) as
    the cheapest.

    Intended for the laundry/dishes use case: the best single start time is
    rarely unique — there's usually a wider span of start times that are
    near-optimal. This function reports that span.

    Example: if the cheapest 1.5h window starts at 15:00 and is "dirt cheap",
    and a 1.5h window starting any time from 11:00 through 16:00 would also
    average out as "dirt cheap", the span is 11:00–16:00 (start times).

    Returns dict with:
      'best':           {'start', 'end', 'avg_price'} — the single cheapest window
      'earliest_start': datetime — earliest start time still in best's zone
      'latest_start':   datetime — latest start time still in best's zone
      'label':          str — the zone label shared by the span

    Returns None if there is insufficient data for even one window.
    """
    if not prices:
        return None

    sorted_prices = sorted(prices, key=lambda p: p['time_start'])
    n = len(sorted_prices)

    full_hours = int(window_hours)
    partial = window_hours - full_hours
    hours_needed = full_hours + (1 if partial > 0 else 0)

    if n < hours_needed:
        return None

    windows: list[dict] = []
    for i in range(n - hours_needed + 1):
        cost = sum(sorted_prices[i + j]['kWh_SEK'] for j in range(full_hours))
        weight = float(full_hours)

        if partial > 0:
            cost += sorted_prices[i + full_hours]['kWh_SEK'] * partial
            weight += partial

        avg = cost / weight
        windows.append({
            'start': datetime.fromisoformat(sorted_prices[i]['time_start']),
            'avg_price': avg,
            'label': price_label(avg),
        })

    best_idx = min(range(len(windows)), key=lambda k: windows[k]['avg_price'])
    best = windows[best_idx]
    target_label = best['label']

    left = best_idx
    while left > 0 and windows[left - 1]['label'] == target_label:
        left -= 1
    right = best_idx
    while right < len(windows) - 1 and windows[right + 1]['label'] == target_label:
        right += 1

    return {
        'best': {
            'start': best['start'],
            'end': best['start'] + timedelta(hours=window_hours),
            'avg_price': best['avg_price'],
        },
        'earliest_start': windows[left]['start'],
        'latest_start': windows[right]['start'],
        'label': target_label,
    }
