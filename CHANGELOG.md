# Changelog

All notable changes to the Weekly Saltwater Fishing Report are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); dates are America/Los_Angeles.
Generated outputs (`conditions_maps/`, `conditions_briefings/`, `past-reports/`) are gitignored and
never committed.

## [2026-07-31b] — Correct the PART 5 permissions claim

### Fixed
- **The "remaining prerequisite" documented earlier the same day was wrong.** The prior entry, the
  README, CLAUDE.md and SKILL.md all stated that macOS **Accessibility** permission was the one
  outstanding blocker for PART 5 and that Ed still had to grant it. Testing disproved this: the
  Claude entries are already enabled in Privacy & Security → Accessibility, and an `osascript` probe
  (`tell application "System Events" to return name of first application process`) returned
  `loginwindow` with **no permission prompt**, confirming Apple Events **Automation** is granted too.
  The claim had been inferred from the helper script's header comment rather than tested. All four
  documents now record both grants as verified present on 2026-07-31 and instruct future runs not to
  report a permissions problem unless `PASTED=` actually fails to advance.
- Consequence: the only cause of the 2026-07-31 map-embed failure was the stale SKILL.md routing
  PART 5 through `request_access`, which is fixed in the previous entry. Nothing is pending on Ed.

## [2026-07-31] — Restore water-color maps, unblock PART 5, fix transcript reader

### Fixed
- **Water-color (chlorophyll) maps returned nothing — NOAA retired the dataset.**
  `noaacwNPPN20S3ASCIDINEOF2kmDaily` now returns **HTTP 404**; the failure was swallowed by
  `build_maps`' per-map `try/except`, so the 2026-07-31 run silently shipped 2 maps instead of 4
  and reported it as ordinary graceful degrade. Replaced the single `CHL_DS` constant with an
  ordered `CHL_DATASETS` fallback chain over the surviving 9 km products, tried in order until one
  answers: `noaacwNPPN20VIIRSDINEOFDaily` (near-real-time, ~2-day lag) →
  `noaacwNPPN20S3ASCIDINEOFDaily` (science, VIIRS+OLCI, ~11-day lag) →
  `noaacwNPPN20VIIRSSCIDINEOFDaily`. NRT leads deliberately: a forward-looking weekly briefing is
  better served by 2-day-old water colour than 11-day-old. `fetch_chl` now also rejects an
  empty or all-NaN grid instead of rendering a blank map, and raises only if **every** dataset fails.
- **Map footers now name the dataset and its lag** (`… · near-real-time 9 km · 2026-07-29 (2-day lag)`)
  rather than hardcoding a sensor string, so a silent product substitution can't be mistaken for
  fresh data. Chlorophyll stride dropped 2/4 → 1 because the surviving grids are 9 km, not 2 km.
- **Intermittent 503s silently dropped temp-break maps.** `coastwatch.pfeg.noaa.gov` — the only host
  serving `jplMURSST41` (the newer `coastwatch.noaa.gov` 404s for it, so a mirror isn't an option) —
  failed ~1 call in 4 under load. Added backoff retry (4 attempts) to `_urlopen`, failing fast on
  permanent 4xx. Verified 4/4 maps across consecutive runs, where the prior code produced 3/4.
- **PART 5 was routed through a permission that cannot exist on a scheduled run.** SKILL.md told the
  run to obtain computer-use (GUI) access, but `request_access` is refused outright during scheduled
  runs and the documented "use Run Now once and Cowork stores the approval" claim is false — the
  session allowlist comes back empty. Meanwhile `tools/dayone_attach.sh` had **already** grown
  `paste`/`clip_paste` subcommands that issue Cmd+V themselves via `osascript` + System Events; only
  the docs still described the legacy `stage`/`clip` + GUI flow. Rewrote PART 5 around the Bash-only
  path, with the real remaining prerequisite (macOS Accessibility permission, a one-time manual grant)
  stated plainly.
- **`dayone_attach.sh list` could embed stale maps.** `newest_map()` used `ls -t <key>_*.png | head -1`,
  i.e. newest match of any date, so on 2026-07-31 — with the chlorophyll source down — it offered the
  **2026-07-14** water-color maps for embedding into a report dated two weeks later. Now date-scoped to
  today's stamp (`FISHING_MAP_STAMP` overrides for replays), printing `MISSING:<file>` to stderr and
  emitting nothing for absent maps. Also fixed a `set -e` abort: the lookup returned non-zero for a
  missing file, which killed the whole `list` loop on the first gap.
- **Transcript reader missed a third panel variant.** The step-4 snippet filtered panels on
  `/transcript/i.test(target-id)`, but the populated panel on the Fisherman's Landing video had
  `target-id = null` — so the reader returned empty through four retries while the transcript was
  fully rendered, producing a bogus "extraction failed". Panels are now selected by **whether they
  contain segment rows**, which is variant-agnostic, with a document-level last resort. Added an
  explicit pre-failure sanity check on the raw segment-row count.
- **Replaced the chunked-transcript retrieval guidance.** Step f said to pull `window._transcript` in
  4,000-char chunks; `javascript_tool` actually truncates its return at ~1,000 chars, making that 20+
  round trips per video with silent-truncation risk. Now: use the reader snippet as the readiness
  probe, then one `get_page_text` call for the content.

### Changed
- Synced the project's reference `SKILL.md` from the live scheduled copy, which had drifted **ahead**
  of it (PART 4 "never hand-write Conditions" block, landing IDs, PDF briefing section were all
  missing from the project copy). The two are now byte-identical.
- CLAUDE.md: corrected the Day One connector prerequisite (Accessibility, not computer-use), the
  chlorophyll data-source description, and the `pip` line (was missing `reportlab`/`pillow`, whose
  absence silently degrades the moon line and kills the PDF — hit on this run's first attempt).

## [2026-07-09] — Fix intermittent YouTube "transcript unavailable" false negatives

### Fixed
- **Root-caused the "some videos extract, others don't in the same run" bug.** YouTube now serves
  two transcript-panel variants bucketed **per video**: classic (`engagement-panel-searchable-transcript`,
  rows `ytd-transcript-segment-renderer`) and modern (`PAmodern_transcript_view`, rows
  `transcript-segment-view-model` with text in `span.ytAttributedStringHost`). The old step-4 selector
  read only the classic panel and only via a synthetic JS `.click()`, so modern-bucketed videos — and
  videos where the synthetic click didn't fire YouTube's fetch — returned empty and were mislabeled
  "transcript unavailable." Verified live: the BDoutdoors latest video populated the classic panel (276
  segments) while the Friedman Adventures latest populated the modern panel (16.2k clean chars, 0 classic
  segments). All 6 channels' latest videos had caption tracks, confirming past "unavailable" notes were
  false negatives, not missing captions.
- Also confirmed the direct fallbacks are dead ends now: the `timedtext` caption URL returns HTTP 200
  with an empty body, and `youtubei/v1/get_transcript` returns `FAILED_PRECONDITION` — both gated. The
  reliable path is a genuine pointer click that lets the player fire its own authenticated fetch.

### Changed
- **SKILL.md Part 1 step 4 rewritten** into a hardened sequence: (a) gate on
  `ytInitialPlayerResponse` caption tracks to distinguish *genuinely* captionless videos from extraction
  failures; (b) expand the description first; (c) **real pointer-click** the *visible* (non-zero-width)
  "Show transcript" button (there's a hidden zero-width duplicate) exactly once; (d) **poll ~12 s** and
  read **both** panel variants via per-segment text; (e) **retry once** on empty; (f) only write
  "transcript unavailable" when the player reports 0 caption tracks.
- **CLAUDE.md Known Behaviors** updated to describe the dual-panel reality and the genuine-vs-failed rule.
- ⚠️ The live scheduled copy at `~/Claude/Scheduled/weekly-saltwater-fishing-report/SKILL.md` is
  read-only from Cowork sessions; synced separately via `update_scheduled_task` (prompt), preserving
  its real Slack channel / alert email config.

### Hardened (after a manual validation run, 2026-07-09)
- **Click/retry logic rewritten** (step 4c/4e). The validation run confirmed the dual-panel *reader*
  works (Chasing Pelagics + Friedman extracted cleanly via the modern panel), but exposed that the
  *trigger* is flaky: real pointer clicks frequently **miss** the button, and a blind second click
  **toggles the panel closed** — so two tackle-video transcripts came back empty and were (correctly)
  flagged "extraction failed — retry next run." Fix: (c) every click is now **verified by the button
  label flipping to "Hide transcript"** (miss ⇒ re-screenshot + re-click; never click a button already
  reading "Hide"); (e) retry is now a **~4-attempt loop** — close/re-open for empty-shell panels,
  re-measure coordinates each try, and a full page reload between attempts to clear stuck toggle state.
- **PART 2** now records the resolved landing IDs (Fisherman's 22, H&M 21, Point Loma 23, Seaforth 20)
  and notes the same-origin fetch shortcut for the archive tables.
- Slack success/skip line now distinguishes "no captions" vs "extraction failed — retry next run."

## [2026-06-27] — Conditions maps now embed as real images (clipboard-paste fix)

### Fixed
- **Maps embed inline instead of a manual PDF drag.** Root-caused the long-standing "image attached
  but blank" symptom: the Day One **CLI's** `--attachments` import is broken in this build (v2026.12.1,
  Mac App Store) — it writes a moment row (filename + identifier) but never copies the bytes
  (`ZHASDATA=0`, no MD5, nothing in `DayOnePhotos/`). Reproduced deterministically across clean args
  (`--`/`[{attachment}]`), `/private/tmp` vs `~/Documents`, and app-running vs app-quit. `install_cli.sh`
  confirms `dayone`/`dayone2` are the same app binary, so no CLI swap or MCP arg fix can help.

### Added
- **`tools/dayone_attach.sh`** — helper for the clipboard-paste embed path (`list` / `count` / `stage`).
  Pasting image data into an open entry creates a real, syncing photo moment
  (`DayOnePhotos/<md5>.png` + `![](dayone-moment://…)` marker), bypassing the broken CLI. Verified 4/4
  maps embed with `ZHASDATA=1`.
- **SKILL.md PART 5** — the insert procedure: per map, `stage` (open entry + clipboard) → computer-use
  `Cmd+V` → `count` verify, re-opening the entry before each paste to keep the cursor anchored and
  avoid focus drift. Self-verifying with one retry per map; PDF remains the fallback.

### Changed
- Day One save still text-only (`create_journal_entry`), now **captures the entry UUID** for PART 5.
- Slack success post reports `Maps: N of 4 embedded`; the manual-PDF ACTION block now appears **only**
  when an embed fails (fallback), not on every run.
- Requires **computer-use (GUI) control approved for the task** — a one-time **Run Now** stores it.

## [2026-06-26] — Conditions briefing add-on + repo packaging

### Added
- **Conditions engine (`conditions.py`).** A headless generator (no Chrome, no login) that produces
  the weekly Conditions section: per-region wind/swell/SST (Open-Meteo, knots), moon (ephem),
  temperature-break maps (NOAA MUR 1 km SST), and water-color maps (VIIRS+OLCI DINEOF gap-filled
  chlorophyll). Eight regions across SoCal + Baja, tiered into core (always) and offshore banks
  (reported only when that week's reports mention them).
- **One-page PDF briefing.** `build_pdf()` composes region tables + four maps into
  `conditions_briefings/conditions_YYYYMMDD.pdf` (brand navy/teal). Auto-pruning of map/PDF files
  older than ~8 weeks.
- **Conditions section placed at the top** of the Day One entry as a forward-looking briefing header.
- **AI-agent repo docs** — `AGENTS.md`, `llms.txt`, `README.md`, `BUILD-PLAN.md`,
  `SPEC-conditions.md`, `SCHEDULE.md`, `CONTRIBUTING.md`, `.gitignore`, `requirements.txt` — mirroring
  the Token-Burn-Dashboard standard.

### Changed
- **Day One save is text-only** (`create_journal_entry`). The connector's `create_entry_with_attachments`
  is broken here (attaches a count but never embeds the bytes → blank placeholders), verified across
  PNG/JPEG/PDF and multiple folders. Maps now ship as the PDF, which Ed adds via Day One's "+" button.
- **Slack success post** now includes the Conditions PDF path as a copyable reminder (local file
  paths aren't clickable in Slack).
- `PROJECT_MAC` in `conditions.py` is overridable via the `FISHING_PROJECT_MAC` env var.

### Fixed
- **Guard against improvised Conditions.** After a dry run hand-wrote the section (wrong units,
  dropped regions, editorial claims) when the script wasn't found, SKILL.md/AGENTS.md now require the
  numbers/moon to come from `conditions.py` verbatim, or the section becomes a single
  "unavailable this run" line — never a fabrication.

### Note
- Conditions is satellite/model-derived: NOAA MUR SST ~1-day lag, chlorophyll ~10-day lag, Baja
  offshore has no buoys (labeled "modeled"). Catalysst remains Ed's interactive tool but is not part
  of the automated run.
