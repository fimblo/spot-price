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
from src.analyze import find_cheapest_window
from src.chart import generate_price_chart
from src.notify import send_message, send_photo

load_dotenv()

TIMEZONE = 'Europe/Stockholm'
REGION = 'SE4'


def _compose_message(prices: list[dict], cheapest: dict) -> str:
    prices_sek = [p['kWh_SEK'] for p in prices]
    daily_avg = sum(prices_sek) / len(prices_sek)

    start = cheapest['start'].strftime('%H:%M')
    end = cheapest['end'].strftime('%H:%M')
    win_avg = cheapest['avg_price'] * 100  # → öre

    return (
        f"<b>Electricity today — {REGION}</b>\n\n"
        f"Daily average: {daily_avg * 100:.1f} öre/kWh\n\n"
        f"Cheapest 1.5 h window:\n"
        f"  {start}–{end}  →  {win_avg:.1f} öre/kWh\n\n"
        f"Start dishes or laundry then!"
    )


def main():
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print("ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.", file=sys.stderr)
        sys.exit(1)

    tz = ZoneInfo(TIMEZONE)
    today = datetime.now(tz).date()

    prices = get_prices(today, REGION)
    if not prices:
        send_message(token, chat_id,
                     f"No spot price data found for {today}.\n"
                     f"Did the fetch script run yesterday?")
        return

    cheapest = find_cheapest_window(prices)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, '..', 'output')
    chart_path = generate_price_chart(prices, str(today), REGION, output_dir=output_dir)

    message = _compose_message(prices, cheapest)

    if chart_path:
        send_photo(token, chat_id, chart_path, caption=message)
    else:
        send_message(token, chat_id, message)


if __name__ == '__main__':
    main()
