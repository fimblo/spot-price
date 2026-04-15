# Development Diary

---

## 2026-04-15 10:30 CET

### Subject: Project kickoff — architecture design, TDD setup, full pipeline implementation

### What I did

Took the prototype (a fetcher, a chart generator, shell helpers) and built a complete Telegram notification pipeline on top of it.

**Architecture decisions:**
- Split the code into four focused modules: `db.py` (SQLite access), `analyze.py` (price analysis), `chart.py` (chart generation), `notify.py` (Telegram). Report scripts orchestrate these.
- Used `python-dotenv` to load Telegram credentials from a `.env` file.
- The evening report covers 21:00–08:00 overnight, combining tonight's remaining prices with tomorrow's early-morning data. This means tomorrow's fetch (which the existing script already supports via `--datediff=1`) must run before 19:00.

**TDD approach:**
- Wrote failing tests for each module before implementing. Mocked `plotly.io.write_image` and `requests.post` to keep tests fast and hermetic.
- Used `pyproject.toml` with `pythonpath = ["."]` so pytest finds `src/` without `sys.path` hacks.
- Confirmed RED state on each test commit before writing the implementation.

**Cheapest window algorithm:**
For a 1.5h window starting at hour `i`: `cost = price[i]*1.0 + price[i+1]*0.5`, `avg = cost/1.5`. Sliding window over sorted hourly prices, `range(n - hours_needed + 1)` to avoid going off the end. The partial-hour weighting matters: `[0.1, 0.4]` gives avg=0.200, not 0.25.

**Bug found in existing code:**
`get-todays-data.py` uses `start.strftime('%Y-%m-%d %H:%m')` — `%m` is month, not minutes. Produces e.g. `2025-02-25 00:02` for February. The new `db.py` uses `substr(time_start, 1, 10)` for date comparison, which is robust against the ISO+timezone format stored by the fetcher.

### Code quality thoughts

The existing scripts were functional but monolithic — DB access, business logic, and output formatting all in one place. The new `src/` separation is more composable and testable. `analyze.py` is the cleanest: a pure function with no side effects.

One awkward spot: the report scripts reach into the project root to resolve `output/` and `database/` paths. Not a problem at two scripts, but would need revisiting if this grew.

The Telegram wrapper (`notify.py`) is intentionally thin. The Bot API is simple enough that pulling in `python-telegram-bot` (an async library) would be overkill.

### Sentiment re: mission

Genuinely useful. Electricity prices in SE4 (and Skåne generally) vary 10–20× within a day. Automating the "when should I run the laundry?" question is a small but real quality-of-life improvement. The pipeline is simple enough to be reliable and the data source (elprisetjustnu.se) is free and stable.
