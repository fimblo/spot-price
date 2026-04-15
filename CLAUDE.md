# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Fetches Swedish electricity spot prices for SE4 (Skåne) region and sends Telegram notifications twice daily: cheapest 1.5-hour window for today (07:00) and tonight's cheapest overnight window (19:00). Useful for deciding when to run dishes or laundry.

## Commands

```bash
# First-time setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
scripts/setup-database.sh
cp .env.example .env          # fill in Telegram credentials

# Fetch spot prices (run after 14:00 — prices for tomorrow are published then)
python scripts/fetch-spot-prices.py [--region SE4] [--datediff 1] [--mock]

# Run reports manually
python scripts/morning-report.py
python scripts/evening-report.py

# Tests
pytest
pytest tests/test_analyze.py          # single module
pytest -k test_finds_cheapest         # single test
```

## Architecture

Two-stage daily pipeline:
1. **Fetch** (cron ~15:00): `scripts/fetch-spot-prices.py` pulls hourly prices from elprisetjustnu.se API → SQLite
2. **Report** (cron 07:00 and 19:00): reads DB, finds cheapest window, generates chart PNG, sends Telegram message

Source modules in `src/`:
- `analyze.py` — `find_cheapest_window()`: sliding-window weighted average to find cheapest N-hour window
- `chart.py` — `generate_price_chart()`: plotly bar chart, colour-coded by price (blue=cheap, red=expensive)
- `notify.py` — `send_message()` / `send_photo()`: thin wrappers over Telegram Bot API
- `db.py` — `get_prices()`: SQLite access; `create_tables()` used by tests for in-memory DBs

Morning report sends a photo with caption. Evening report finds the cheapest overnight window (21:00–08:00) using tonight's remaining prices plus tomorrow's early-morning prices.

## Cron example

```cron
00 15 * * * cd /path/to/spot-price && .venv/bin/python scripts/fetch-spot-prices.py
00 07 * * * cd /path/to/spot-price && .venv/bin/python scripts/morning-report.py
00 19 * * * cd /path/to/spot-price && .venv/bin/python scripts/evening-report.py
```

## Environment variables

Copy `.env.example` to `.env`:
- `TELEGRAM_BOT_TOKEN` — from @BotFather
- `TELEGRAM_CHAT_ID` — the group/channel to post in; get it via @userinfobot or the `getUpdates` API endpoint
