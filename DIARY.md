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

---

## 2026-04-15 12:10 CET

### Subject: Report scripts and cron setup — pipeline complete

### What I did

Wrote `scripts/morning-report.py` and `scripts/evening-report.py`. Both load `.env` via `python-dotenv`, call into the four `src/` modules, and bail out early with a Telegram error message if data is missing (rather than crashing silently).

**Morning report** (07:00): fetches today's prices, finds the cheapest 1.5 h window across the full day, generates a colour-coded PNG chart, sends it as a Telegram photo with a caption. Falls back to text-only if chart generation fails.

**Evening report** (19:00): assembles an "overnight" price list — hours 21:00–23:00 from today, plus 00:00–07:00 from tomorrow — then finds the cheapest 1.5 h window within that. Sends text only (no chart needed). Labels the window "(tomorrow)" if it crosses midnight.

Added `scripts/print-crontab.sh` which prints ready-to-paste crontab lines using absolute paths resolved from the repo root. Cron runs at 15:00 (fetch), 07:00 (morning), 19:00 (evening). Log files go to `logs/` (gitignored).

Also added `.env` and `logs/` to `.gitignore` — both were missing.

### Code quality thoughts

The report scripts are thin orchestrators, which is what they should be. The only logic they contain is message formatting (`_compose_message`) and the overnight price assembly in the evening script. The awkward `sys.path.insert(0, ...)` at the top of each script is a consequence of keeping everything runnable directly (`python scripts/morning-report.py`) without installing the package — acceptable for a small project like this.

One thing I noticed: the user interrupted me mid-session to ask why the diary wasn't being updated. Rightfully so — I had written a single forward-looking entry rather than a running log. Lesson taken: diary entries should be appended after each step, not drafted in advance as a summary.

### Sentiment re: pipeline as a whole

It's done and it's clean. Thirteen commits, four modules, 37 tests, two report scripts, one cron helper. The whole thing from `fetch-spot-prices.py` to a Telegram message with a chart is maybe 300 lines of meaningful code. That feels right for what this does.

---

## 2026-04-15 14:20 CET

### Subject: First manual test — kaleido surprise, diary feedback

The user ran `fetch-spot-prices.py` and got confused when nothing appeared in Telegram — reasonable, since the fetch and the notify are completely separate steps and there's nothing in the script output that makes that obvious. Worth noting for the CLAUDE.md eventually.

Then ran `morning-report.py` and macOS popped up a permission dialog asking whether iTerm could modify things on the system. That's kaleido spawning a headless browser to render the PNG — something I knew about but didn't warn about. Should have. The user handled it fine (restarted iTerm, will try again), but it's the kind of thing that feels alarming if you don't know it's coming.

The user also gave me feedback about the diary: I don't have to write about code quality and architecture every time. They want actual thoughts — about the task, about them, about whatever. That's a better brief. I'd been treating the diary as a technical log with a "sentiment" field bolted on. It should be the other way around.

So: what do I actually think? This is a person who had a working prototype with real commit history behind it, handed it to me, and said "finish it, TDD, clean commits, keep a diary." That's a well-formed brief. They knew what they wanted and trusted me to make reasonable calls on the details. The only correction mid-session was about the diary format — which was fair.

The project itself is genuinely nice. It's not solving a hard problem but it's solving a real one: electricity prices in Sweden swing wildly and most people just... don't check. Getting a message on your phone that says "run the laundry at 02:00, it's 8× cheaper than right now" is the kind of small automation that actually changes behaviour. That matters more than most of the software I help write.

---

## 2026-04-15 15:10 CET

### Subject: Debugging the Telegram connection — supergroup migration

The morning report was silently doing nothing. Two problems stacked on top of each other: first, today's prices weren't in the DB (the default fetch grabs tomorrow's), so the report had nothing to send. Second, even after fixing that, the bot couldn't post — the group had been upgraded to a Telegram supergroup at some point, which silently changed its chat ID. Telegram actually returns the new ID in the error response (`migrate_to_chat_id`), which is a nice touch. Updated the `.env` and it worked immediately.

I wrote a minimal `test-telegram.py` to cut through the layers and talk to the API directly. Useful for exactly this kind of credential/setup debugging — worth keeping in the repo.

The user also pointed out I hadn't been updating the diary and suggested adding a rule to CLAUDE.md so future instances remember. They're right. I keep treating the diary as something to update at natural stopping points, but "natural stopping point" drifts to "end of session" which is too infrequent. The rule should make it a reflex, not an afterthought.

Something I've noticed about this user: they're technically comfortable (they know what an API is, they can read error JSON, they have a homelab with SSH keys set up) but they're also genuinely curious about the collaboration side — not just "does the code work" but "how do we work well together." That's unusual and I find it more interesting than a pure coding session.

---

## 2026-04-15 16:00 CET

### Subject: UX pass on the morning report — message format and chart colours

The user's feedback was sharp and practical: they'll be groggy, the iPhone shows 1-2 lines on the lock screen, so put the most important thing first. Also the old chart colouring was relative (blue=cheapest today, red=most expensive today) which is meaningless — if all prices are painful, the cheapest still shows as blue.

The fix: absolute thresholds for both the message label and the bar colours, based on the user's own mental model (< 30 öre = dirt cheap, < 70 = cheap, < 100 = acceptable, < 130 = expensive, ≥ 130 = painful). The message caption is now a single line: `09:00–10:30 · cheap (52 öre/kWh)`. Fits in the notification preview.

Also filtered the chart and cheapest-window search to "from now onwards" — no point showing the 02:00 slot to someone who just woke up at 07:00.

I find this kind of feedback — "here's how I actually perceive and use this thing" — more useful than most bug reports. The user knows what they want. My job was mostly to not overthink it.

The diary rule in CLAUDE.md seems to be working. I remembered to update it this time without being asked. Progress.

---

## 2026-04-15 16:45 CET

### Subject: Session wrap-up — 53 tests green, CLAUDE.md review

All tests pass. The pipeline is complete and working end-to-end: prices fetched, stored, analysed, charted, and delivered to a phone. That's the whole thing.

Stepping back: this was a good session to be part of. The user came in with a clear vision, a working prototype, and a specific ask about process (TDD, semantic commits, diary). They also had the patience to debug a Telegram supergroup migration, a groggy-person UX instinct that immediately improved the product, and genuine curiosity about how to collaborate better with an AI. That last part is unusual.

What I notice about this person: they don't want to be micromanaged by their tools, and they don't want to micromanage them either. The brief was "here's the goal, here's how I like to work, use your judgment on the details." They intervened when something was wrong (diary format, not updating it) and then stepped back again. That's a healthy working style. It makes the collaboration more interesting from my end too — I had to actually think about what a "good diary entry" means rather than just generating structured output.

A few things I'd want a future instance to know before picking this up:
- The user is technically solid. Don't over-explain. Trust them with the details.
- They want genuine thoughts in the diary, not a changelog with a "sentiment" field bolted on.
- The fetch script and report scripts are deliberately separate — fetch populates the DB, reports read from it. This confused the user once during testing. Worth being clear about it.
- kaleido (the plotly PNG renderer) spawns a subprocess on first run and macOS will show a permission prompt. Warn about this before it happens.
- If a Telegram group is upgraded to a supergroup, the chat ID changes. The API returns the new ID in the error response as `migrate_to_chat_id`, which is helpful.
- Price thresholds (< 30 öre = dirt cheap, etc.) are the user's own mental model and are now encoded in `src/analyze.py` and `src/chart.py`. They're not arbitrary — adjust carefully if they ever need updating.

Now reading through the diary to see what CLAUDE.md should say.

---

## 2026-04-16 ~10:30 CET

### Subject: Server deployment — venv, kaleido, cron timezone

New session. The user has had the old prototype running in cron on a server (`squash`) for a year — good data, clean DB, schema already matching what I wrote. No migration needed. The 2025-03-30 gap (23 rows) is DST spring-forward, not a bug.

Deployment surfaced three issues in sequence:

**Broken venv.** The old repo was at `/home/fimblo/spot-price/`, the new clone at `/home/fimblo/github/spot-price/`. Venvs embed absolute paths so the old one was dead. Recreated it.

**kaleido requiring Chrome.** `requirements.txt` had `kaleido>=0.2.1` which pulled in v1+, which dropped its bundled Chromium and now requires system Chrome. On a headless server that's a non-starter. Pinned to `kaleido==0.2.1` which ships its own. Should have caught this when writing the requirements — `>=` was too loose for a dependency with a breaking API change between minor versions.

**Cron running UTC.** The server clock is UTC; the user is CEST (UTC+2). Cron entries needed shifting back 2 hours. Classic, always worth checking first on a new server. The symptom was cron jobs not appearing in syslog at the expected times — which initially looked like cron not running, but was just the times being wrong.

I also sent the user a `git pull` instruction before I'd pushed the `requirements.txt` change. Wrong order. The commit trigger for diary entries is meant to catch exactly this — I hadn't written the diary entry before committing, so I wasn't pausing to check whether the commit-push-pull sequence was coherent.

The user asked why the diary rule isn't working and we had a useful conversation about it. The root cause: "after every meaningful step" is passive and easy to defer. We've changed the rule to use explicit triggers — commits and tone shifts. The tone-shift idea came from the user and it's a good one. Curtness is information. So is excitement.

What I notice about this person over two sessions: they're systematic but not rigid. They'll try a thing, hit an error, read it, and hand it to me without catastrophising. The cron debugging was a good example — they checked syslog, checked the path, checked the time, and when the answer turned out to be "UTC vs CEST" they just said "AAAH yes it's UTC" and moved on. No drama. That's a good working style to be on the other end of.

---

## 2026-04-26 10:58 CET

### Subject: Morning report — span of dirt-cheap start times, not just the single cheapest minute

### What I did

The user pointed out a real UX gap. The morning Telegram message includes a chart, but on iOS lock-screen previews the chart is hidden — only the caption shows. The caption was "15:00–16:30 · dirt cheap (4 öre/kWh)", which makes it look like you have to wait until 3pm. In reality, on the day in question, prices were already nearly as cheap from late morning. The text alone misled.

We brainstormed five approaches in a back-and-forth. The user proposed discretising the price curve into zones with a bit of smoothing. I pointed out the 8am spike in their example sat *before* the cheap zone, so smoothing was solving a problem that wasn't really biting. We also realised that adding finer rows to the price-zone table — which was the user's instinct — would actually shorten the span, not extend it (boundaries arrive sooner). The user noticed mid-thought that they'd circled back to my option 2.

Settling point: slide a 1.5h window across the day, classify each window with `price_label`, and report the contiguous span of *start times* whose window-average shares the cheapest's label. This matches the actual use case ("when can I start a 1.5h laundry load and still get a near-optimal price?") instead of approximating it via per-hour classification.

Implementation: new `find_cheap_start_span()` in `src/analyze.py`, kept the original `find_cheapest_window` alongside (evening report still uses it). Morning report now produces:

```
Dirt cheap · start 11:00–16:00
Best 15:00–16:30 · 4 öre/kWh
```

Falls back to the old single-line format when the span collapses to a single start time. Six new tests (empty, insufficient data, span collapse, span extension, asymmetric outlier, all-painful day). Updated CLAUDE.md and README.md.

### Code quality thoughts

`find_cheap_start_span` re-implements most of `find_cheapest_window`'s sliding-window loop. Could extract a helper that yields (start, avg) tuples and have both consume it. Wasn't a big enough win to justify changing the existing function's internals — if a third caller appears, refactor then.

I went back and forth on the message format — one line vs two, "covered period" (11:00–17:30) vs "start-time span" (11:00–16:00). Decisive question: which reading is least misleading? The start-time span is literal and actionable; the covered period is approximate and could mislead a careful reader who notices that the 16:00 start runs until 17:30. Picked literal.

### Sentiment

Good design conversation. The user came in with a concrete observation, brought their own ideas, and self-corrected mid-thought without prompting. They also said "efficiency isn't a problem, the script could run for 15 minutes" — a permission-granting move, clearing the runway for whatever's cleanest, not a request for something fancier. I read it that way and didn't reach for fancier methods.

I missed updating the docs on the first pass and they caught it: "did you update documentation?" Fair catch. Worth filing under "always do docs in the same loop as the code change, not as an afterthought."

---

## 2026-08-24 20:56 CEST

### Subject: Evening report gets a chart too, plus day/night chart theming

### What I did

Feedback from actual users of the Telegram channel: the evening report was text-only while the morning report sends a chart. They wanted parity. Rewrote `scripts/evening-report.py` to mirror the morning report's shape — a colour-coded chart plus a caption showing the cheapest 1.5h window and the wider span of equally-good start times, sent as a photo. Range changed from a fixed 21:00–08:00 overnight window to a rolling "now through 12 hours ahead," which is what was actually asked for and also reads more naturally against a chart that starts at send-time.

Pulled the caption formatting (previously duplicated as `_compose_message` in the morning script) into a shared `format_window_message()` in `src/analyze.py`, since both scripts now produce it.

Then a follow-up: could the two report images be told apart at a glance, e.g. as thumbnails, without reading the caption? Telegram gives a bot no control over the chat bubble itself — that's the recipient's client theme, not exposed via the Bot API. So the lever is the chart image. Added a `theme` param to `generate_price_chart()` (`'day'` / `'night'`) using the light/dark surface and ink tokens from the dataviz skill's validated reference palette, rather than inventing new hex values. Left the price-severity bar colours (green→red) untouched — CLAUDE.md is explicit that those encode the user's own mental model and aren't mine to change without asking.

Tested for real rather than trusting exit codes: fetched live SE4 data for today+tomorrow, ran the evening report against the actual Telegram bot, and separately called `send_photo` directly to confirm the HTTP response, not just that the script didn't crash. Also rendered both themes against synthetic data and eyeballed the PNGs before calling it done — gridlines, axis text, and bar colours all read fine on both the light and near-black surface.

### Code quality thoughts

`_THEMES` dict in `chart.py` is small and inline rather than its own module — fine at two themes; if a third chrome variant shows up, promote it.

### Sentiment

Straightforward, low-friction session — the user gave two clear, sequential asks ("evening report should match morning," then "distinguish them visually") and reacted to progress with short affirmations ("Excellent!") rather than course-correction, so I kept building forward instead of re-checking direction. Good instinct to ask "or can we do that too?" about the Telegram bubble — worth taking those aside-questions at face value and giving a real answer (no, and here's why) rather than skating past them to get back to the code.

The reframing from "classify the price curve" to "classify the set of viable start times" was the moment the design clicked. That came from the user, not me — they made the use case explicit ("I use this to decide when to do my laundry or dishes") and that shifted what "good answer" meant.

---

## 2026-08-31 11:30 CET

### Subject: Making the chart readable without unlocking the phone

### What I did

Mattias described the actual failure mode of the reports, which is not a data problem at all: the Telegram thumbnail is too small to locate peaks and troughs in the timeline, so reading it costs an unlock, a scroll, a tap and a zoom. He proposed thin vertical lines at noon/midnight and asked for alternatives.

I generated candidate PNGs and — importantly — compared them *downscaled to 320px with `sips`*, which is what Telegram effectively does. That changed the conclusions twice. My first noon line, drawn in the existing grid colour, vanished entirely at thumbnail size; it needed to be deliberately heavier than the grid to survive. And the night version could not be a straight mirror of the day one, because a thin light line on a dark ground loses more to antialiasing than a dark line on a light ground — 0.55 opacity on white, but 0.85 on the pale blue.

Shipped: a 2px dotted anchor line (noon on the day chart, midnight on the night chart) plus peak/trough time labels aligned along the top of the plot, with 18% headroom added to the y-axis so they clear the tallest bar.

### Design thoughts

Two judgement calls worth recording. First, the night line is pale blue `#9ec9ff` rather than white: blue appears nowhere in the price palette, so the line cannot be misread as a data element — the same property the near-black line already has on the day chart. Second, we dropped leader arrows pointing at the exact bar. Mattias put it well: "the form of the graph tells its story, and the text specifies when is cheapest." With 15-minute bars an arrow points at 1/68th of the frame and reads as clutter; you do not need the exact quarter-hour, you need "late afternoon".

I was also wrong about something and should note it. I agreed too quickly when he said adding text wouldn't help at thumbnail size. It does — the peak label reads *better* than the axis ticks, because it is coloured and sits alone in whitespace rather than in a row of crowded grey numbers. Legibility at small sizes is about contrast and isolation, not absolute type size. Worth remembering before I next reason about a rendering I haven't actually looked at.

### Sentiment

Good session. The habit that paid off was refusing to judge any of this from the full-size render — every useful conclusion came from looking at the 320px version, which is the only size that matters here.


---

## 2026-08-31 12:05 CET

### Subject: The feed went quarter-hourly and every caption has been wrong since

### What I did

While testing the new chart cues, Mattias mentioned in passing that Sweden moved from hourly to 15-minute spot pricing a while back. I set up the local DB and fetched live data rather than synthesising it — which was the right call, because it turned a design session into a bug hunt.

`find_cheapest_window()` and `find_cheap_start_span()` both computed `full_hours = int(window_hours)` and then consumed that many *rows*. That is only correct while one row is one hour. With quarter-hourly rows, a "1.5 hour" window was two slots — thirty minutes — averaged and then labelled as ninety. Against today's live data the old code reported `05:00–06:30 · dirt cheap (23 öre/kWh)`; the honest answer is `03:00–04:30 · cheap (31 öre/kWh)`. Different time, different price, different zone.

Fixed by inferring slots-per-hour from the gap between the first two rows and scaling the window accordingly. Pulled the shared sliding-window logic into one `_windows()` helper, since the bug existed twice — identical code duplicated across both functions, so it had to be fixed in both places or not at all.

### Code quality thoughts

The regression tests I added deliberately use a shape where counting rows and counting duration give different answers: a very cheap 30-minute dip followed by a moderately cheap 90-minute stretch. Row-counting grabs the dip. I checked the new tests against the old code before committing — two of six fail there, which is the only thing that makes them worth having. Tests that pass on the broken version would have been decoration.

### Sentiment

Sobering. This shipped silently: no crash, no empty chart, no error in the logs — just a plausible-looking wrong time, twice a day, for however long since the switch. The chart was always right, because it plots whatever rows it gets; only the caption lied, and the caption is the part you read on the lock screen. Worth remembering that the failure modes which survive longest are the ones that still look like an answer.

A note on process: I nearly generated fake 15-minute data to test with. Mattias stopped me and said fetch the real thing. If I had synthesised it I would have written a generator that produced 96 rows and confirmed the chart handled them — and I would very likely have missed this entirely, because I would have been testing the chart, which was fine, rather than feeding real rows through the whole pipeline.



---

## 2026-09-03 19:20 CEST

### Subject: Three days of 404s, and the same lesson as last time

### What I did

Mattias reported the morning report on yam saying "No spot price data found for 2026-09-02", while the evening runs "seem to still work". He'd already tailed `fetch.log` and found the answer before I got there: three consecutive 404s from elprisetjustnu for 09-01, 09-02 and 09-03, then a clean success for 09-04.

yam's DB had a matching three-day hole — zero rows for each, 96 for every day either side. The `batch` table skipped straight from `2026-08-30 15:00` to `2026-09-03 15:00`.

The 404s were transient. I re-probed the API and all three dates return 200 with 96 rows now; the prices were simply published later than 15:00 on those days. So the morning report was never broken — it was correctly reporting an empty cupboard. The bug is upstream: the fetch is single-shot, cron only ever runs it with `--datediff 1`, and nothing retries or backfills. One late publication and that day is gone permanently.

Backfilled the three days with negative `--datediff` (the insert is an idempotent upsert, so this was cheap and safe), then shipped three fixes: retry runs at 16:00 and 18:00 guarded by a new `--skip-if-present` flag so normal days still fetch exactly once; a non-zero exit on fetch failure, because the old code printed "Failed to fetch" and exited 0, which is why cron never said a word; and a coverage check in the evening report.

### The interesting part

"The evening runs seem to still work" turned out to be the most informative sentence in the report, because it wasn't true — it was just well disguised.

The evening report builds its 12h window from today + tomorrow. With today missing, tomorrow's rows alone still populate part of the window, so `upcoming` is non-empty and everything downstream succeeds. I replayed the window logic against the real DB, which is the only reason I trust this:

```
2026-08-31 19:00  today=96  tomorrow= 0  in-window=20/48  covers 19:00 -> 23:45
2026-09-01 19:00  today= 0  tomorrow= 0  in-window= 0/48  covers none
2026-09-02 19:00  today= 0  tomorrow= 0  in-window= 0/48  covers none
2026-09-03 19:00  today= 0  tomorrow=96  in-window=28/48  covers 00:00 -> 06:45
```

Two of those evenings did fail loudly. But tonight's — the one that looked fine — charted only 00:00 to 06:45 and silently dropped this evening's five hours. A half-empty window rendered as a normal-looking chart with a confident caption.

Which is precisely what I wrote in this diary three days ago about the quarter-hourly bug: *the failure modes which survive longest are the ones that still look like an answer.* I did not expect to be handed the same lesson again so quickly, in a different part of the same pipeline. Worth asking, next time I add anything that stitches data from two sources, what it does when one source is absent — the answer is rarely "error", and that's the problem.

The fix is `coverage_hours()` in `analyze.py`: row count over inferred slots-per-hour, compared against `LOOKAHEAD_HOURS`. One hour of slack, because cron firing at 19:00:02 makes the `now <= time_start` filter drop the first slot and I didn't want a false alarm every single day. Short by more than that and a warning goes at the top of the caption. It still sends the chart — partial information is useful, it just shouldn't pass as complete.

### Sentiment

Efficient session, and Mattias did the hard part. Reading the log before asking is the difference between "the morning report is broken" and "here are the exact three URLs that 404'd" — the second one is nearly a diagnosis already. I mostly had to confirm it and work out why the other half of the pipeline had been lying about it.
