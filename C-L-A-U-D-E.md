# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Fetches Swedish electricity spot prices for SE4 (Skåne) region and sends Telegram notifications twice daily: a price chart with the cheapest 1.5-hour window for the rest of today (07:00) and one for the next 12 hours overnight (19:00). Useful for deciding when to run dishes or laundry.

## Commands

```bash
# First-time setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
scripts/setup-database.sh
cp .env.example .env          # fill in Telegram credentials

# Fetch spot prices — only populates the DB, sends nothing to Telegram
python scripts/fetch-spot-prices.py --datediff 1   # tomorrow (default, run after 14:00)
python scripts/fetch-spot-prices.py --datediff 0   # today (use this to test reports immediately)
python scripts/fetch-spot-prices.py --mock         # use sample data from etc/sample-mock.json
python scripts/fetch-spot-prices.py --skip-if-present   # no-op if that date is already stored (retry runs)
python scripts/fetch-spot-prices.py --datediff -2  # backfill a past day the fetch missed
python scripts/fetch-spot-prices.py --alert-on-failure   # Telegram ping if it fails (last retry only)

# Run reports manually (reads DB and sends to Telegram)
python scripts/morning-report.py
python scripts/evening-report.py

# Verify Telegram credentials work before running reports
python scripts/test-telegram.py

# Tests
pytest
pytest tests/test_analyze.py          # single module
pytest -k test_finds_cheapest         # single test
```

## Architecture

Two-stage daily pipeline:
1. **Fetch** (cron ~15:00): `scripts/fetch-spot-prices.py` pulls prices from elprisetjustnu.se API (15-minute slots, 96 rows/day) → SQLite. **Does not send anything to Telegram.**
2. **Report** (cron 07:00 and 19:00): reads DB, finds cheapest window, generates chart PNG, sends Telegram message

Source modules in `src/`:
- `analyze.py` — `find_cheapest_window()`: sliding-window weighted average to find cheapest N-hour window; `find_cheap_start_span()`: same sliding window, but also returns the contiguous span of start times whose window-average shares the cheapest's price label (used by both reports so a text-only lock-screen notification doesn't mislead the reader into waiting for the single cheapest minute when a wider window is just as good); `format_window_message()`: renders a `find_cheap_start_span()` result as the caption both reports send; `price_label()`: categorises a price as "dirt cheap" / "cheap" / "acceptable" / "expensive" / "painful"
- `chart.py` — `generate_price_chart()`: plotly bar chart, colour-coded by absolute price thresholds
- `notify.py` — `send_message()` / `send_photo()`: thin wrappers over Telegram Bot API
- `db.py` — `get_prices()`: SQLite access; `create_tables()` used by tests for in-memory DBs

Both reports send a photo with caption, in the same format: a colour-coded chart plus a caption showing the cheapest 1.5h window *and* the wider span of start times that would still be in the same price zone, so a text-only notification on a lock screen still conveys "you can start any time in this range" rather than just the single optimal start. `format_window_message()` in `src/analyze.py` renders that caption; both scripts share it.

Morning report covers the rest of today, from the current hour onward. Evening report covers the next 12 hours from send time (e.g. 19:00 tonight through ~07:00 tomorrow), combining today's remaining prices with tomorrow's early-morning prices fetched earlier in the day.

## Price thresholds

The user's own mental model, encoded in `src/analyze.py` and `src/chart.py`. Don't change without checking with them.

| Range          | Label       | Chart colour |
|----------------|-------------|--------------|
| < 30 öre/kWh   | dirt cheap  | green        |
| < 70 öre/kWh   | cheap       | light green  |
| < 100 öre/kWh  | acceptable  | yellow       |
| < 130 öre/kWh  | expensive   | orange       |
| ≥ 130 öre/kWh  | painful     | red          |

## Cron example

Run `bash scripts/print-crontab.sh` for ready-to-paste lines using absolute paths for this machine. Manual example:

```cron
00 15 * * * cd /path/to/spot-price && .venv/bin/python scripts/fetch-spot-prices.py
00 16 * * * cd /path/to/spot-price && .venv/bin/python scripts/fetch-spot-prices.py --skip-if-present
00 18 * * * cd /path/to/spot-price && .venv/bin/python scripts/fetch-spot-prices.py --skip-if-present --alert-on-failure
00 07 * * * cd /path/to/spot-price && .venv/bin/python scripts/morning-report.py
00 19 * * * cd /path/to/spot-price && .venv/bin/python scripts/evening-report.py
```

The 16:00 and 18:00 lines are retries for days where elprisetjustnu publishes
late. `--skip-if-present` makes them no-ops once the day is stored, so a normal
day still fetches exactly once.

## Diary

`DIARY.md` is a running log of thoughts, decisions, and observations — not just a technical changelog. Entries should be timestamped and written in first person. Technical notes are welcome but not required — the diary is also for observations about the user, the collaboration, and the mission.

**When to write an entry — treat these as triggers, not suggestions:**

- **Every git commit.** Write the diary entry before or immediately after committing. The commit is the forcing function; the diary entry is part of the same act. Do not push without updating the diary.
- **Noticeable tone shifts.** If the user becomes visibly excited or noticeably curt, something significant just happened — something worth capturing. Excitement means something landed; curtness often means something didn't. Either way, note it.

The rule has historically been stated as "after every meaningful step" — that phrasing is too passive and easy to defer. Use the triggers above instead.

## Environment variables

Copy `.env.example` to `.env`:
- `TELEGRAM_BOT_TOKEN` — from @BotFather
- `TELEGRAM_CHAT_ID` — the group/channel to post in; get it via @userinfobot or the `getUpdates` API endpoint

## Known gotchas

**Fetch vs report are separate.** Running `fetch-spot-prices.py` only writes to the database — it sends nothing to Telegram. If a report finds no data, it means the relevant fetch hasn't run yet (`--datediff 0` for today, `--datediff 1` for tomorrow).

**Late publication means a missed day is missed forever — unless a retry runs.** The API 404s for a date it hasn't published yet, and the fetch is single-shot. On 2026-09-01/02/03 the 15:00 run 404'd three days running (the data appeared later), which left a three-day hole in the DB and made the morning report say "No spot price data found". Hence the 16:00/18:00 retry lines. `fetch-spot-prices.py` now exits non-zero on failure, so cron can actually surface it; backfill a past day with a negative `--datediff`. yam has no MTA and no `MAILTO`, so a non-zero exit alone reaches nobody — the 18:00 line carries `--alert-on-failure`, which pings Telegram. Only the *last* retry alerts, deliberately: a 15:00 failure is usually just a late publication that 16:00 or 18:00 will pick up, and an alert that fires on those would be trained away.

**A missing day can hide inside the evening report.** It builds its 12h window from today + tomorrow, so one missing day still leaves enough rows to draw a plausible-looking chart of only half the night — it looks healthy while silently dropping hours. It now compares `coverage_hours()` against `LOOKAHEAD_HOURS` and prepends a warning to the caption when the window is short by more than an hour.

**kaleido on macOS.** On first run, `morning-report.py` generates a PNG via kaleido, which spawns a subprocess. macOS may show a permission dialog asking if your terminal app can "modify" the system. Click Allow — it's expected behaviour.

**Telegram supergroup migration.** If a group was upgraded to a supergroup, its chat ID silently changes. The API returns the new ID in the error response as `migrate_to_chat_id`. Update `TELEGRAM_CHAT_ID` in `.env` accordingly.
