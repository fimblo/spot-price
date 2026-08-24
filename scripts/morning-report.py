#!/usr/bin/env python3
"""
Morning report — run at 07:00 local time.

Sends today's spot prices as a colour-coded chart, plus the cheapest
1.5-hour window (good for starting laundry or dishes).
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.db import get_prices
from src.analyze import find_cheap_start_span, format_window_message
from src.chart import generate_price_chart
from src.notify import send_message, send_photo

load_dotenv()

TIMEZONE = 'Europe/Stockholm'
REGION = 'SE4'


def main():
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print("ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.", file=sys.stderr)
        sys.exit(1)

    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    today = now.date()
    current_hour = now.hour

    prices = get_prices(today, REGION)
    if not prices:
        send_message(token, chat_id,
                     f"No spot price data found for {today}.\n"
                     f"Did the fetch script run yesterday?")
        return

    # Only consider hours from now onwards — no point showing a window that has passed
    remaining = [p for p in prices if int(p['time_start'][11:13]) >= current_hour]
    span = find_cheap_start_span(remaining or prices)

    # Chart shows from current hour onwards — skip history the user can't use
    chart_prices = [p for p in prices if int(p['time_start'][11:13]) >= current_hour]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, '..', 'output')
    chart_path = generate_price_chart(chart_prices, str(today), REGION, output_dir=output_dir, theme='day')

    message = format_window_message(span)

    if chart_path:
        send_photo(token, chat_id, chart_path, caption=message)
    else:
        send_message(token, chat_id, message)


if __name__ == '__main__':
    main()
