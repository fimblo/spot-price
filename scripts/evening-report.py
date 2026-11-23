#!/usr/bin/env python3
"""
Evening report — run at 19:00 local time.

Sends spot prices from now through 14:00 tomorrow as a colour-coded chart,
plus the cheapest 1.5-hour window in that span (good for starting laundry or
dishes overnight, or knowing it pays to wait until tomorrow's midday dip) —
same format as the morning report, just centred on the evening-to-next-day
stretch instead of the rest of today.

14:00 is roughly where the next fetch takes over: tomorrow's prices are stored
by the 15:00 run, and the next evening report picks up from 19:00 again.
"""
import os
import sys
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.db import get_prices
from src.analyze import find_cheap_start_span, format_window_message, coverage_hours
from src.chart import generate_price_chart
from src.notify import send_message, send_photo

load_dotenv()

TIMEZONE = 'Europe/Stockholm'
REGION = 'SE4'
WINDOW_END = time(14, 0)  # chart/search window runs until this time tomorrow
COVERAGE_SLACK_HOURS = 1  # tolerated shortfall before the window counts as gappy


def main():
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print("ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.", file=sys.stderr)
        sys.exit(1)

    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    today = now.date()
    tomorrow = today + timedelta(days=1)
    window_end = datetime.combine(tomorrow, WINDOW_END, tzinfo=tz)
    window_label = WINDOW_END.strftime('%H:%M')

    all_prices = get_prices(today, REGION) + get_prices(tomorrow, REGION)
    if not all_prices:
        send_message(token, chat_id,
                     f"No spot price data found for {today}.\n"
                     f"Did the fetch script run today?")
        return

    # Chart/search window: from now through WINDOW_END tomorrow, spanning
    # midnight. If the data stops earlier, the chart simply ends earlier.
    upcoming = [p for p in all_prices
                if now <= datetime.fromisoformat(p['time_start']) < window_end]

    if not upcoming:
        send_message(token, chat_id,
                     f"Could not find price data between now and {window_label} tomorrow.\n"
                     f"Has tomorrow's fetch run? (scripts/fetch-spot-prices.py --datediff 1)")
        return

    span = find_cheap_start_span(upcoming)

    # The window is stitched from two days, so a missing day still leaves
    # enough rows to draw a plausible-looking chart of only half the night.
    # Say so rather than letting a partial window pass as a normal one.
    covered = coverage_hours(upcoming)
    expected = (window_end - now).total_seconds() / 3600
    shortfall = expected - covered
    warning = None
    if shortfall > COVERAGE_SLACK_HOURS:
        first = datetime.fromisoformat(upcoming[0]['time_start']).strftime('%H:%M')
        last = datetime.fromisoformat(upcoming[-1]['time_end']).strftime('%H:%M')
        warning = (f"\u26a0 Only {covered:.1f}h of the {expected:.0f}h until {window_label} have prices "
                   f"({first}\u2013{last}) \u2014 a fetch has failed.")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, '..', 'output')
    chart_path = generate_price_chart(
        upcoming, f'{today}-evening', REGION, output_dir=output_dir, theme='night')

    message = format_window_message(span)
    if warning:
        message = f"{warning}\n\n{message}"

    if chart_path:
        send_photo(token, chat_id, chart_path, caption=message)
    else:
        send_message(token, chat_id, message)


if __name__ == '__main__':
    main()
