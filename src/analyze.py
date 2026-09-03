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


def _slots_per_hour(sorted_prices: list[dict]) -> float:
    """
    Infer how many rows cover one hour, from the gap between the first two.

    The feed used to be hourly and is now quarter-hourly, so one row can no
    longer be assumed to be one hour. Falls back to 1 when there is too little
    data to measure a gap.
    """
    if len(sorted_prices) < 2:
        return 1.0

    first = datetime.fromisoformat(sorted_prices[0]['time_start'])
    second = datetime.fromisoformat(sorted_prices[1]['time_start'])
    minutes = (second - first).total_seconds() / 60

    if minutes <= 0:
        return 1.0
    return 60 / minutes


def coverage_hours(prices: list[dict]) -> float:
    """
    How many wall-clock hours these slots actually cover.

    Rows are equal-duration slots, so this is simply the row count divided by
    the inferred slots-per-hour. Lets a caller tell a full window from one that
    is only half-populated — a report that charts whatever rows it found will
    otherwise render a partial window as though it were a normal one.
    """
    if not prices:
        return 0.0

    sorted_prices = sorted(prices, key=lambda p: p['time_start'])
    return len(sorted_prices) / _slots_per_hour(sorted_prices)


def _windows(prices: list[dict], window_hours: float) -> list[dict]:
    """
    Average price of every window of window_hours that fits in prices.

    Rows are equal-duration slots, so a window is the mean of the slots it
    covers. A window that ends mid-slot weights that final slot by the fraction
    it uses — with hourly rows and a 1.5h window that is the old
    "one full hour plus half the next"; with quarter-hourly rows the same
    window is six whole slots and no fraction at all.

    Returns a list of {'start': datetime, 'avg_price': float}, in time order,
    or [] when there is not enough data for even one window.
    """
    if not prices:
        return []

    sorted_prices = sorted(prices, key=lambda p: p['time_start'])
    n = len(sorted_prices)

    total_slots = window_hours * _slots_per_hour(sorted_prices)
    # Guard against float drift making an exact slot count look fractional
    if abs(total_slots - round(total_slots)) < 1e-9:
        total_slots = float(round(total_slots))

    full_slots = int(total_slots)
    partial = total_slots - full_slots
    slots_needed = full_slots + (1 if partial > 0 else 0)

    if slots_needed == 0 or n < slots_needed:
        return []

    windows = []
    for i in range(n - slots_needed + 1):
        cost = sum(sorted_prices[i + j]['kWh_SEK'] for j in range(full_slots))
        weight = float(full_slots)

        if partial > 0:
            cost += sorted_prices[i + full_slots]['kWh_SEK'] * partial
            weight += partial

        windows.append({
            'start': datetime.fromisoformat(sorted_prices[i]['time_start']),
            'avg_price': cost / weight,
        })

    return windows


def find_cheapest_window(prices: list[dict], window_hours: float = 1.5) -> Optional[dict]:
    """
    Find the cheapest time window of given duration.

    Args:
        prices: list of dicts with 'time_start' (ISO string) and 'kWh_SEK' (float)
        window_hours: duration in hours (default 1.5)

    Returns:
        dict with 'start' (datetime), 'end' (datetime), 'avg_price' (float/kWh_SEK)
        or None if there is insufficient data for even one window.
    """
    windows = _windows(prices, window_hours)
    if not windows:
        return None

    best = min(windows, key=lambda w: w['avg_price'])
    return {
        'start': best['start'],
        'end': best['start'] + timedelta(hours=window_hours),
        'avg_price': best['avg_price'],
    }


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
    windows = _windows(prices, window_hours)
    if not windows:
        return None

    for w in windows:
        w['label'] = price_label(w['avg_price'])

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


def format_window_message(span: dict) -> str:
    """
    Format a find_cheap_start_span() result as a short caption/message.

    Shared by the morning and evening reports so both read the same way:
    one line when the cheapest window is effectively unique, two lines
    (zone + span, then the single best window) when a wider span of start
    times is just as good.
    """
    best = span['best']
    best_start = best['start'].strftime('%H:%M')
    best_end   = best['end'].strftime('%H:%M')
    ore        = best['avg_price'] * 100
    label      = span['label']

    earliest = span['earliest_start'].strftime('%H:%M')
    latest   = span['latest_start'].strftime('%H:%M')

    if earliest == latest:
        return f"{best_start}–{best_end} · {label} ({ore:.0f} öre/kWh)"

    return (
        f"{label.capitalize()} · start {earliest}–{latest}\n"
        f"Best {best_start}–{best_end} · {ore:.0f} öre/kWh"
    )
