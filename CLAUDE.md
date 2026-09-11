# Weekly Saltwater Fishing Report — Project Instructions

> **Configuration note (public repo):** `<ALERT_EMAIL>`, `<SLACK_WORKSPACE>`, and
> `<SLACK_CHANNEL_ID>` are placeholders. The real values live in the gitignored `CONFIG.local.md`
> and in the live Cowork scheduled task. Fill them in (or keep them local) before relying on alerts.

## What This Project Does

This project runs a weekly automated fishing intelligence report every Friday at 9:02 AM. Claude scrapes YouTube transcripts, San Diego landing fish count archives, and long range boat reports, generates a **Conditions** briefing (wind / swell / SST / moon + temperature-break and water-color/chlorophyll maps + a **Storm Watch** block covering named East Pacific tropical storms and hurricanes from NOAA's National Hurricane Center), then compiles everything into a structured Day One journal entry in the **Saltwater Fishing Journal**. The Conditions section sits at the **top** of the report as a forward-looking briefing header. Images (4 Conditions maps, the NHC 7-day outlook, one forecast cone per named storm) are attached at save time from Day One's sandbox-readable inbox and positioned inline with `[{attachment}]` placeholders.

## Scheduled Task

- **Task ID:** `weekly-saltwater-fishing-report`
- **Schedule:** Every Friday at 9:02 AM (Pacific)
- **Output:** Day One journal entry → Saltwater Fishing Journal
- **Tags:** fishing, saltwater, weekly-report, SoCal, Baja
- **Alert email:** <ALERT_EMAIL>
- **Alert/notify Slack channel:** #fishing-report-alerts (workspace <SLACK_WORKSPACE>, ID `<SLACK_CHANNEL_ID>`, private)
- **Notifications:** success post to Slack on every run; on error, Gmail + Slack in parallel, Apple Notes fallback

The task runs autonomously. Chrome must be open with the Claude in Chrome extension active at run time.

## Editing the Task Instructions

The live task instructions are managed by Cowork's scheduler at:
`~/.claude/scheduled-tasks/weekly-saltwater-fishing-report/SKILL.md`

To update the task (add channels, change sources, adjust format):
1. Open this project in Cowork
2. Use the `/schedule` skill and reference the `SKILL.md` file in this folder as the new instructions
3. Or edit the Scheduled SKILL.md directly in the Cowork app

The `SKILL.md` in this project folder is the **working reference copy** — keep it in sync with the Scheduled version after any changes.

## Required Connectors (must be active on Fridays)

| Connector | Purpose | Status Check |
|-----------|---------|-------------|
| Claude in Chrome extension | SD landing fish count pages + LongRangeSportfishing; YouTube transcripts **only as the per-video fallback** (primary path is headless `tools/yt_transcript.py`) | Must have Chrome open |
| Day One MCP | Saves the report with `create_journal_entry(attachments=[…])`, passing the `<!-- ATTACHMENTS -->` list from `conditions.py` **verbatim** (inbox paths inside Day One's group container — the sandboxed app cannot read any other location). The text carries one `[{attachment}]` per image. Then `tools/dayone_attach.sh trigger <uuid>` opens the entry so Day One performs its lazy import and polls the photo count (SKILL.md PART 5). No keystrokes, no computer-use, no Accessibility grant. | Day One app installed and running; `~/Library/Group Containers/5U8NS4GX82.dayoneapp2/` present |
| Sandbox bash + network | Runs `conditions.py` (Open-Meteo + NOAA MUR). **No Chrome or login needed** for this step | Allowlisted network reaches open-meteo.com + coastwatch.pfeg.noaa.gov |
| Gmail MCP | Sends error alert emails (in parallel with Slack) | Gmail connected |
| Slack MCP | Success post every run + error alert (parallel with Gmail) → #fishing-report-alerts | Slack connected + app in channel |
| Apple Notes MCP | Fallback alert only if both Gmail and Slack fail | Apple Notes connected |

> **Note:** The Conditions section does NOT depend on Chrome. Browser screenshots cannot be
> saved to disk on the scheduled run, so the temp-break maps are rendered headlessly from NOAA
> MUR data into real PNG files (via `conditions.py`) rather than screenshotted from Catalysst.
> Catalysst remains Ed's richer *interactive* tool but is not part of the automated run.
> The NHC images (7-day outlook, forecast cones) are plain PNGs downloaded from stable URLs, so they
> need no browser either.

## YouTube Channels Monitored

1. BDoutdoors — https://www.youtube.com/@bdoutdoorsdotcom-m4p
2. Friedman Adventures Podcast — https://www.youtube.com/@FriedmanAdventuresPodcast
3. Dancing on Water — https://www.youtube.com/@DancingonWater1203
4. Arthur Pereira — https://www.youtube.com/@ArthurPereira1974
5. Chasing Pelagics — https://www.youtube.com/@ChasingPelagics
6. Fisherman's Landing — https://www.youtube.com/@fishermanslanding

To add or remove channels: edit SKILL.md Part 1.

## SD Landing Sites Monitored

- Fisherman's Landing — sandiegofishreports.com
- H&M Landing — sandiegofishreports.com
- Point Loma Sportfishing — sandiegofishreports.com
- Seaforth Sportfishing — sandiegofishreports.com

## Long Range Source

- LongRangeSportfishing.net — all boat reports from the past 7 days

## Weekly Conditions (Wind / Swell / SST / Moon + Temp-Break Maps + Storm Watch)

- Generated by `conditions.py` (see SKILL.md PART 4). Run: `python3 "conditions.py"` after
  `pip3 install matplotlib numpy ephem reportlab pillow --break-system-packages -q`.
  **All five are required** — `ephem` missing degrades the moon line and `reportlab`/`pillow` missing
  kills the PDF, both silently (the 2026-07-31 run hit exactly this on its first attempt).
- Outputs the Conditions Markdown to stdout (region lines, the **Storm Watch** block, and one
  `[{attachment}]` placeholder per image), renders the PNGs in `conditions_maps/` (2 temp-break +
  2 water-color + NHC 7-day outlook + one 5-day cone per named storm), copies every image into Day
  One's inbox `~/Library/Group Containers/5U8NS4GX82.dayoneapp2/Data/Documents/CLI-Inbox/`, and
  compiles a dated **PDF briefing** at `conditions_briefings/conditions_YYYYMMDD.pdf`. Prints the
  PDF's macOS path in a `<!-- BRIEFING -->` footer and the ordered inbox paths in an
  `<!-- ATTACHMENTS -->` footer. All three folders auto-prune files older than ~8 weeks.
- **Image delivery (rewritten 2026-09-11 — the previous method never worked unattended):** the run
  passes the ATTACHMENTS list verbatim as `attachments=` to `create_journal_entry`, then runs
  `tools/dayone_attach.sh trigger <uuid>` (SKILL.md PART 5). Why this works when everything before it
  didn't: Day One is the sandboxed App Store build. Its attachment import (a) reads the file
  **lazily, the first time the entry is displayed**, and (b) can only read files **inside its own
  group container**. Every earlier attempt attached files from `/tmp` or `~/Documents` → a moment
  was recorded but the bytes were never imported ("blank placeholder"). The same file attached from
  `CLI-Inbox/` imports within ~5 s of `open "dayone://edit?entryId=<uuid>"`. Verified 2026-09-11:
  6 of 6 images (4 maps + outlook + Norbert cone) embedded on a test entry, positioned by placeholder.
  ⛔ **The clipboard-paste path is dead — do not resurrect it.** System Events keystrokes, the Edit ▸
  Paste menu item, and hardware-level CGEvent Cmd+V all reach Day One, but its editor ignores them
  (screen unlocked, app frontmost, text area focused — tested 2026-09-11). It embedded 0 of 4 maps on
  every scheduled run from 2026-07-31 through 2026-09-11; the only 4/4 run (2026-07-24) was
  interactive. `paste` / `clip_paste` now print a warning and exit 3.
- **Storm Watch:** East Pacific only; named storms (TS/HU) always print, a depression only when it
  threatens a region. Tiers: **IMPACT** (34-kt wind field within 60 nm of a region point in the
  5-day track), **WATCH** (closest approach < 300 nm), **MONITOR** (no regional threat). A formation
  line prints when NHC's 7-day odds are ≥ 60%. Every line links its NHC page, so the value is
  delivered even if an image fails. The 7-day outlook graphic is the **first** storm image
  (caption "Tropical / Hurricane — NOAA NHC East Pacific 7-day outlook"), followed by one cone per
  named storm. Storm images come after the four Conditions maps.
- **Attach only this run's images:** the ATTACHMENTS footer / `conditions_maps/attachments_<stamp>.txt`
  are written fresh each run; `dayone_attach.sh list` and `inbox` are date-scoped to today's stamp.
  Expect fewer images on degraded runs — the placeholder count always matches the list.
- **Regions:** Core (always) = SoCal Bight, Northern Baja, San Clemente & Catalina. Banks (modeled,
  include only when this week's reports mention them) = Tanner/Cortez, Cedros/Guadalupe, Mag Bay,
  The Ridge, Alijos Rocks.
- **Data:** wind/swell/SST = Open-Meteo; Storm Watch = NOAA NHC (`CurrentStorms.json`, TCM advisory
  text, TWO outlook text/graphic — all public, no key); temp-break maps = NOAA MUR 1 km SST (CoastWatch ERDDAP);
  water-color maps = DINEOF gap-filled chlorophyll (CoastWatch ERDDAP, `CHL_DATASETS` fallback chain
  in `conditions.py` — near-real-time 9 km first at ~2-day lag, science-quality 9 km as backstops;
  the dataset and lag actually used are printed under each map); moon = ephem.
  ⚠️ The former 2 km dataset `noaacwNPPN20S3ASCIDINEOF2kmDaily` was **retired by NOAA and now 404s**
  (root cause of the missing water-color maps on 2026-07-31). If water-color maps go missing again,
  re-check the chain against the live ERDDAP catalog rather than assuming a transient outage.
- **Reliability:** `_urlopen` retries with backoff on 5xx/429. `coastwatch.pfeg.noaa.gov` (the only
  host serving `jplMURSST41` — the newer `coastwatch.noaa.gov` 404s for it) returns sporadic 503s;
  without the retry a single 503 silently dropped one temp-break map from a run.
- To tune region coordinates or add a region, edit the `REGIONS` list in `conditions.py`.

## Known Behaviors / Notes

- **YouTube transcripts come from `tools/yt_transcript.py` first (2026-09-09), Chrome second.** Channel Atom feeds give exact publish dates, Shorts are dropped by probing `youtube.com/shorts/<id>` (200 = Short, 303 = normal), and the text is fetched with `youtube_transcript_api` under `/usr/bin/python3`. Why: the Chrome transcript panel has a per-video failure where it opens and never populates (Chasing Pelagics, 2026-09-04, four retries incl. reload) and the in-page caption-URL fallback now returns an empty body (Proof-of-Origin token required); the library fetched that same video in one call. YouTube can rate-limit the library (`IpBlocked`, hit once in testing at ~20 fetches/10 min) — the script stops at the first block, and the Chrome fallback was verified to still work from the same IP while blocked. Never re-run the script into a block.
- The Chrome fallback (below) requires Chrome to be fully loaded and signed in
- YouTube serves multiple transcript-panel variants bucketed **per video** — rows are either `ytd-transcript-segment-renderer` (classic) or `transcript-segment-view-model` (modern). The extractor (SKILL.md Part 1 step 4) must read **both** row types; a classic-only selector silently returns empty on modern-bucketed videos, the root cause of intermittent "transcript unavailable" false negatives (same run, some videos fine). Fixed 2026-07-09: gate on `ytInitialPlayerResponse` caption tracks (genuine-vs-failed), expand description, real pointer-click the visible (non-zero-width) "Show transcript" button, poll ~12 s, read both row types, retry. Only mark "transcript unavailable" when the player has **0 caption tracks**.
- **Never select the transcript panel by `target-id`** (fixed 2026-07-31). Panels appear with `target-id` of `engagement-panel-searchable-transcript`, `PAmodern_transcript_view`, **and `null`**. The null case is real — it hit the Fisherman's Landing video on 2026-07-31 and made a `target-id`-filtered reader return empty through four retries while the transcript was fully rendered. Select panels by **whether they contain segment rows**. Before ever reporting an extraction failure, check `document.querySelectorAll('ytd-transcript-segment-renderer, transcript-segment-view-model').length` — if it's > 0 the bug is the selector, not YouTube.
- **Retrieve transcripts with `get_page_text`, not chunked JS reads.** Once the panel is populated, one `get_page_text` call returns the whole transcript; `javascript_tool` truncates its return at ~1,000 chars, so chunking a 12k–25k-char transcript costs 20+ round trips per video and risks silent truncation. Use the reader snippet only as the readiness probe.
- SD landing fish count pages require clicking the current month's archive link; the URL pattern is `?landing_id=XX&month=M&year=YYYY#historicals`
- If Chrome is not open when the task fires, it will send an alert email and stop
- Day One entry is tagged: fishing, saltwater, weekly-report, SoCal, Baja
- Conditions maps are rendered headlessly (no Chrome). If NOAA MUR is unreachable, the report
  posts without maps and notes "Temp-break maps unavailable this week" — this is NOT an alert.
- If the NHC feeds are unreachable the Storm Watch block prints as "unavailable this run" — NOT an
  alert. If `trigger` reports fewer images than expected, post anyway; the Slack ACTION block asks Ed
  to open the entry (which itself completes the import) or drag the PDF in.
- `conditions.py` re-fetches live data each run; map files are timestamped (`*_YYYYMMDD.png`) so
  older maps accumulate in `conditions_maps/` — safe to prune periodically.

## Project Folder Structure

```
weekly-saltwater-fishing-report/
├── CLAUDE.md          ← This file (project instructions for Claude)
├── SKILL.md           ← Reference copy of the task instructions
├── SETUP.md           ← Connector setup and troubleshooting guide
├── conditions.py          ← Generates Conditions text + Storm Watch + maps + the PDF briefing (PART 4)
├── conditions_maps/       ← Rendered map/storm PNGs + attachments_<stamp>.txt (auto-pruned >8 wks)
├── conditions_briefings/  ← Dated PDF briefings Ed drags into the Day One entry (auto-pruned >8 wks)
└── past-reports/          ← Optional: archive exported Day One entries here
```
