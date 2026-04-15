# Development Diary

---

## 2026-04-15 10:15 CET

### Subject: Project kickoff — architecture decisions and documentation

### What I did

Reviewed the existing prototype: `fetch-spot-prices.py` (pulls from elprisetjustnu.se, stores in SQLite), `get-todays-data.py` (queries DB, produces a plotly chart), and a handful of shell helpers. Planned out the full pipeline and wrote `CLAUDE.md`, `DIARY.md`, and `.env.example`.

Architecture settled on: four focused `src/` modules (`db`, `analyze`, `chart`, `notify`) orchestrated by two thin report scripts. Added `requirements.txt` and `pyproject.toml` (pytest config with `pythonpath = ["."]` to avoid sys.path hacks).

### Code quality thoughts

The existing code works but is monolithic — everything inline in each script. Worth keeping as-is for now; the new modules will sit alongside them.

### Sentiment

Good starting point. Clean scope: fetch once a day, report twice. The data source is free and has been stable.

---

## 2026-04-15 10:45 CET

### Subject: TDD cycle — `analyze.py` (cheapest window)

### What I did

Wrote 9 tests for `find_cheapest_window()` before touching the implementation. Confirmed RED (import error), committed, then implemented and got GREEN.

The algorithm: sliding window over sorted hourly prices. For a 1.5 h window at index `i`: `cost = price[i]*1.0 + price[i+1]*0.5`, `avg = cost/1.5`. `range(n - hours_needed + 1)` bounds the loop so there's always enough data for a complete window. Works for arbitrary `window_hours` including whole numbers (e.g. 2.0h).

### Code quality thoughts

`analyze.py` is the cleanest module — pure function, no I/O, no side effects, trivially testable. The partial-hour weighting is the only real subtlety: `[0.1, 0.4]` correctly yields 0.200, not 0.25.

### Sentiment

Satisfying. The core logic is small and correct. Tests document the algorithm's behaviour precisely.

---

## 2026-04-15 11:00 CET

### Subject: TDD cycle — `db.py` (database access layer)

### What I did

Wrote 11 tests using `tmp_path` fixtures and an in-memory-style SQLite file. Confirmed RED, committed, then implemented `create_tables()` and `get_prices()`.

Found a bug in the existing `get-todays-data.py` while writing the new module: `start.strftime('%Y-%m-%d %H:%m')` uses `%m` (month number) instead of `%M` (minutes). For February this produces `00:02` instead of `00:00` — a silent off-by-two-minutes filter. Fixed in `db.py` by using `substr(time_start, 1, 10)` for date comparison, which is also robust against the `+01:00` timezone suffix stored in the ISO timestamps.

### Code quality thoughts

`create_tables()` being exposed publicly is a small pragmatic call — tests need it to set up an in-memory schema. It's idempotent (`CREATE IF NOT EXISTS`) so no risk in calling it twice.

### Sentiment

The bug find was worthwhile. The fix is robust. DB layer is thin and honest.

---

## 2026-04-15 11:20 CET

### Subject: TDD cycle — `chart.py` (plotly bar chart)

### What I did

Wrote 7 tests, mocking `plotly.io.write_image` so the suite stays fast with no actual image rendering. Confirmed RED, committed, then implemented `generate_price_chart()` (refactored from `get-todays-data.py`).

Colour scheme: normalised price → blue (cheap) to red (expensive). Y-axis in öre (×100) for readability. Output path: `output/spot-price-{date}-{region}.png`.

### Code quality thoughts

Mocking `pio.write_image` is the right call — generating actual PNGs in CI would require kaleido and be slow. The mock tests verify the interface (called once, with `format='png'`) without caring about the image content.

### Sentiment

Fine. Chart generation is the least interesting part of the pipeline but it's what makes the morning message worth opening.

---

## 2026-04-15 11:35 CET

### Subject: TDD cycle — `notify.py` (Telegram Bot API wrapper)

### What I did

Wrote 10 tests mocking `requests.post`. Confirmed RED, committed, then implemented `send_message()` and `send_photo()`. Both return `bool`; all exceptions are caught and return `False`.

Deliberately thin — raw `requests` calls to the Bot API rather than pulling in `python-telegram-bot` (which is async and much heavier than needed here).

### Code quality thoughts

The wrapper is almost too thin to justify a module, but it's the right boundary: it isolates all Telegram-specific knowledge (URL shape, payload keys, file upload format) in one place, and the mock tests enforce that the report scripts never need to know those details.

### Sentiment

Good. Telegram's Bot API is pleasantly simple for this use case.
