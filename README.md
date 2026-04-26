# spot-price

Fetches Swedish electricity spot prices (SE4 / Skåne) and sends twice-daily Telegram notifications:

- **07:00** — span of equally-good start times for a 1.5-hour load, plus the single cheapest window, with a colour-coded price chart
- **19:00** — cheapest overnight window (21:00 tonight → 08:00 tomorrow)

Useful for deciding when to run laundry or dishes.

## Setup

```bash
# 1. Create virtualenv and install dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Create the database
bash scripts/setup-database.sh

# 3. Configure Telegram credentials
cp .env.example .env
# Edit .env — fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
```

Get your bot token from [@BotFather](https://t.me/BotFather). Get the chat ID via `@userinfobot` or the `getUpdates` API endpoint. If in doubt, run `python scripts/test-telegram.py` to verify credentials before going further.

## One-shot test (manual run)

```bash
source .venv/bin/activate

# Fetch today's prices into the DB (the default --datediff 1 fetches tomorrow)
python scripts/fetch-spot-prices.py --datediff 0

# Send the morning report
python scripts/morning-report.py

# Send the evening report
python scripts/evening-report.py
```

The fetch and report steps are deliberately separate. Running `fetch-spot-prices.py` only writes to the database — it sends nothing to Telegram.

## Cron setup

Run this to get ready-to-paste crontab lines with absolute paths for your machine:

```bash
bash scripts/print-crontab.sh
```

Then add them to your crontab (`crontab -e`). The schedule is:

| Time  | Script                  | What it does                        |
|-------|-------------------------|-------------------------------------|
| 15:00 | `fetch-spot-prices.py`  | Pull tomorrow's prices into the DB  |
| 07:00 | `morning-report.py`     | Send chart + cheapest window today  |
| 19:00 | `evening-report.py`     | Send cheapest overnight window      |

Logs go to `logs/` (gitignored). The fetch runs at 15:00 because elprisetjustnu.se publishes tomorrow's prices around 14:00.

## Price thresholds

| Range          | Label      | Chart colour |
|----------------|------------|--------------|
| < 30 öre/kWh   | dirt cheap | green        |
| < 70 öre/kWh   | cheap      | light green  |
| < 100 öre/kWh  | acceptable | yellow       |
| < 130 öre/kWh  | expensive  | orange       |
| ≥ 130 öre/kWh  | painful    | red          |
