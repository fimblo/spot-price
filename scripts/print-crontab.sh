#!/usr/bin/env bash
# Prints ready-to-paste crontab lines for the spot-price pipeline.
# Run with:  crontab -e   then paste the output below.

REPO="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$REPO/.venv/bin/python"

cat <<EOF
# spot-price pipeline
# Fetch tomorrow's prices after they're published (~14:00)
0 15 * * *  cd "$REPO" && "$PYTHON" scripts/fetch-spot-prices.py >> logs/fetch.log 2>&1

# Retries, in case the prices were published late. --skip-if-present makes
# these no-ops once the day is stored, so a normal day still fetches once.
# The 18:00 run alerts: an hour before the evening report, a still-missing
# tomorrow means that report will be short, and that is worth knowing.
0 16 * * *  cd "$REPO" && "$PYTHON" scripts/fetch-spot-prices.py --skip-if-present >> logs/fetch.log 2>&1
0 18 * * *  cd "$REPO" && "$PYTHON" scripts/fetch-spot-prices.py --skip-if-present --alert-on-failure >> logs/fetch.log 2>&1

# Last chance for TODAY, half an hour before the morning report. The lines
# above all ask for tomorrow, so a day the API published after 18:00 would
# otherwise never be fetched at all. --skip-if-present makes this a no-op on
# a normal day; when it does fire, it is the difference between a morning
# report and a "No spot price data found" message.
30 6 * * *  cd "$REPO" && "$PYTHON" scripts/fetch-spot-prices.py --datediff 0 --skip-if-present --alert-on-failure >> logs/fetch.log 2>&1

# Morning report: today's prices + cheapest daytime window
0  7 * * *  cd "$REPO" && "$PYTHON" scripts/morning-report.py >> logs/morning.log 2>&1

# Evening report: cheapest overnight window (21:00–08:00)
0 19 * * *  cd "$REPO" && "$PYTHON" scripts/evening-report.py >> logs/evening.log 2>&1
EOF

echo ""
echo "Also make sure the logs/ directory exists:"
echo "  mkdir -p $REPO/logs"
