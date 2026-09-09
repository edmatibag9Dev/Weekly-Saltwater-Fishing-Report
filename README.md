# Weekly Saltwater Fishing Report

An automated weekly fishing-intelligence report for Southern California & Baja. Every Friday it
compiles YouTube fishing intel, San Diego landing fish counts, and long-range boat reports into a
single **Day One** journal entry — led by a forward-looking **Conditions** briefing (wind, swell,
SST, moon, and temperature-break + water-color maps) built entirely from free public data.

## Overview / Purpose

This answers "what's been biting, where, and what will the water be doing this week?" A Cowork
scheduled task (Friday 9:02 AM Pacific) pulls the week's transcripts from six YouTube channels
headlessly (`tools/yt_transcript.py` — channel feeds + `youtube_transcript_api`, Chrome only as a
per-video fallback), scrapes four San Diego landings and LongRangeSportfishing.net through the Chrome
extension, then runs a headless **Conditions engine** (`conditions.py`) that pulls live numbers and
renders maps with no Chrome and no logins. Everything
lands in one Day One entry: the Conditions maps are embedded as real photo moments by pasting image
data into the saved entry (the Day One connector's own attachment import is broken — it records a
moment without the bytes), with a one-page PDF built alongside as a portable fallback. Built for Ed,
who reads the report on Day One's desktop and mobile apps.

## Features

- **Conditions briefing header** — moon (phase + illumination), and per-region wind (knots), swell,
  and SST, with a tiered region list (core nearshore always; offshore banks only when fished).
- **Temperature-break maps** — NOAA MUR 1 km SST for SoCal and Baja, with contour breaks.
- **Water-color maps** — DINEOF gap-filled chlorophyll (clean-blue vs. green-water edges), fetched
  through a fallback chain of NOAA datasets so one retired product can't blank the map; each map
  footer names the dataset and its lag.
- **One-page PDF briefing** — region tables + every map produced that run, brand-styled, dated,
  auto-pruned >8 wks.
- **YouTube / landing / long-range intel** — what's biting, lures & techniques, where, fish counts.
- **Resilient by design** — numbers from a JSON API, maps rendered headlessly; a Conditions failure
  is non-fatal (the report still posts).
- **Honest data** — Baja offshore values are labeled "modeled"; the run never invents numbers.

## Files

| File | Role |
|---|---|
| `conditions.py` | Conditions engine — Open-Meteo numbers, NOAA MUR + chlorophyll maps, ephem moon, reportlab PDF |
| `SKILL.md` | The scheduled-task prompt (sources, report format, Slack/alert protocol) |
| `CLAUDE.md` | Project instructions, required connectors, known behaviors |
| `AGENTS.md` | Canonical AI-agent guide (file map, data contract, how-to-extend) |
| `SPEC-conditions.md` | Conditions data contract — regions, coordinates, sources, output |
| `SCHEDULE.md` | How the weekly Cowork task is configured/edited |
| `BUILD-PLAN.md` | Architecture, decisions, findings |
| `CHANGELOG.md` / `CONTRIBUTING.md` | History / commit + doc standards |
| `tools/yt_transcript.py` | Headless YouTube step — channel Atom feeds → drop Shorts → newest captioned upload → transcript via `youtube_transcript_api`; one status line per channel |
| `tools/dayone_attach.sh` | Embeds the run's maps into the saved Day One entry (clipboard paste via osascript) |
| `requirements.txt` | Python deps for `conditions.py` |
| `conditions_maps/`, `conditions_briefings/`, `youtube_transcripts/` | Generated outputs (gitignored; auto-pruned after ~8 weeks) |

## How to Use

**Generate the Conditions section + PDF (no Chrome needed):**

```bash
cd ~/Documents/Claude/Projects/"Weekly Saltwater Fishing Report"
pip install -r requirements.txt --break-system-packages -q
python3 conditions.py
```

This prints the ready-to-paste Conditions Markdown and writes
`conditions_briefings/conditions_YYYYMMDD.pdf`. The full weekly report (with the Chrome-scraped
intel) is produced by the Cowork scheduled task — see SCHEDULE.md.

**Pull this week's YouTube transcripts (no Chrome needed):**

```bash
/usr/bin/python3 tools/yt_transcript.py --days 7
```

Prints one status line per channel (`OK` / `NO_NEW_VIDEO` / `NO_CAPTIONS` / `FETCH_FAILED` /
`FEED_FAILED`) and writes `youtube_transcripts/YYYYMMDD/<channel>.txt` plus a `manifest.json`.
Use `/usr/bin/python3` literally — the library is installed for the system Python, not Homebrew's.
Only `FETCH_FAILED` / `FEED_FAILED` channels go through the Chrome fallback in SKILL.md Part 1.

**Embed the maps into a saved entry** (after the Day One entry exists — needs its UUID):

```bash
UUID="<entry uuid>"
mapfile -t MAPS < <(bash tools/dayone_attach.sh list)   # today's maps only
bash tools/dayone_attach.sh paste      "$UUID" "${MAPS[0]}"
for m in "${MAPS[@]:1}"; do bash tools/dayone_attach.sh clip_paste "$UUID" "$m"; done
bash tools/dayone_attach.sh count "$UUID"               # must equal ${#MAPS[@]}
```

## Configuration

Personal settings live in `SKILL.md` / `CLAUDE.md`: the alert **email**, the **Slack** workspace +
`#fishing-report-alerts` channel ID, and the Day One **journal** name ("Saltwater Fishing Journal").
On a public clone, replace these with your own (or scrub to placeholders and keep real values in a
gitignored `CONFIG.local.md`).

## Data Sources

| Source | Used for | Freshness |
|---|---|---|
| [Open-Meteo Marine](https://marine-api.open-meteo.com/) + [Weather](https://api.open-meteo.com/) | Wind (kt), swell, SST numbers per region | 7-day forecast, live |
| [NOAA CoastWatch ERDDAP](https://coastwatch.pfeg.noaa.gov/erddap/griddap/jplMURSST41.html) — `jplMURSST41` | Temperature-break maps (MUR 1 km SST) | ~1-day lag |
| [NOAA CoastWatch ERDDAP](https://coastwatch.noaa.gov/erddap/) — `CHL_DATASETS` chain: `noaacwNPPN20VIIRSDINEOFDaily` → `noaacwNPPN20S3ASCIDINEOFDaily` → `noaacwNPPN20VIIRSSCIDINEOFDaily` | Water-color (chlorophyll) maps | ~2-day lag (NRT) / ~11-day (science backstops) |
| `ephem` | Moon phase + illumination | Computed, no network |
| 6 YouTube channels — public Atom feed (`youtube.com/feeds/videos.xml?channel_id=…`) + [`youtube_transcript_api`](https://pypi.org/project/youtube-transcript-api/) 1.2.4 | Bite intel, lures, locations | Newest captioned non-Short upload in the last 7 days; Chrome UI is the per-video fallback |
| [sandiegofishreports.com](https://www.sandiegofishreports.com/) · [longrangesportfishing.net](https://www.longrangesportfishing.net/fishreports.php) | Dock counts, boat reports | Scraped weekly via Chrome |

All sources are public HTTP with no keys or logins.

## Known Limitations / Workarounds

- The Day One connector cannot embed attachments, so maps are embedded by pasting image data into
  the saved entry via `tools/dayone_attach.sh` (`paste` / `clip_paste`). Those subcommands send the
  keystroke themselves through `osascript`, so the step runs from Bash and needs **no computer-use
  grant** — which matters because computer-use access cannot be approved during a scheduled run. It
  does need two macOS grants, **Accessibility** and **Automation** (Apple Events → System Events /
  Day One); both were verified present on 2026-07-31 and are not currently a blocker. If the paste
  fails, the run still posts and the Slack message carries the PDF path as a manual fallback.
- Conditions data is satellite/model-derived: NOAA MUR SST lags ~1 day, chlorophyll ~2 days on the
  near-real-time product (~11 on the science-quality backstops), and Baja offshore has no buoys —
  useful for planning, not ground truth.
- Embed only the current run's maps. `dayone_attach.sh list` is date-scoped and reports
  `MISSING:<file>` on stderr; fewer than four maps is normal when a source is down.
- `dayone_attach.sh count` prints `?` (not `0`) when the Day One database cannot be read — it reads
  a snapshot copy under an 8 s cap so it can never hang PART 5 (it did on 2026-08-07). Treat `?` as
  "unknown", never as "no photos embedded".
- **YouTube can rate-limit the transcript library** (`IpBlocked` / `RequestBlocked`). Hit on
  2026-09-08 after ~20 fetches in 10 minutes of testing; a normal weekly run makes 5–8. The script
  stops fetching at the first block and marks the remaining channels `FETCH_FAILED … not attempted`;
  those go through the Chrome fallback, which was verified to still work from the same IP while the
  library was blocked. Re-running the script only deepens the block.
- **Channel feeds include Shorts** and do not flag them. The script probes `youtube.com/shorts/<id>`
  (HTTP 200 = Short, 303 = normal video) and skips them; on 2026-09-08 three of Fisherman's Landing's
  six newest uploads were 20-second clips with no captions. If the probe errors twice the video is
  treated as normal and a `⚠` is printed rather than risk dropping a real report.
- The 7-day window is hour-granular (now − 7 × 24 h). A Tuesday post against a Friday run leaves a
  3-day margin; a run that slips a day can miss it — `--days 8` widens the window if that recurs.

## Troubleshooting

- **Water-color maps missing.** Most likely a retired ERDDAP dataset ID, not a transient outage —
  this is exactly how `noaacwNPPN20S3ASCIDINEOF2kmDaily` failed in July 2026 (it began returning
  HTTP 404). Check the live catalog before writing it off:
  `https://coastwatch.noaa.gov/erddap/search/index.json?searchFor=DINEOF+chlor`, then extend
  `CHL_DATASETS` in `conditions.py`.
- **A temp-break map is missing but the other rendered.** `coastwatch.pfeg.noaa.gov` — the only host
  serving `jplMURSST41` — returns sporadic 503s. `_urlopen` retries with backoff; a persistent
  failure means the dataset or host changed.
- **Moon line or PDF missing.** The environment is missing `ephem` or `reportlab`/`pillow`; both
  degrade silently. Re-run `pip install -r requirements.txt --break-system-packages -q`.
- **`FETCH_FAILED … IpBlocked`** from `tools/yt_transcript.py`. YouTube is rate-limiting this IP,
  not a script bug. Do not re-run; use the Chrome fallback for the printed URLs. Two weeks running
  is the signal to add `yt-dlp` with a PO-token provider.
- **`ModuleNotFoundError: youtube_transcript_api`.** Wrong interpreter or a wiped user site.
  `/usr/bin/python3 -m pip install --user youtube-transcript-api`, then re-run.
- **A channel shows `NO_NEW_VIDEO` but you can see a new video on YouTube.** Check the status line's
  `[skipped …]` list — it was probably classified as a Short. The manifest records the probe result.
- **Chrome fallback: "Transcript extraction failed."** Before trusting it, check
  `document.querySelectorAll('ytd-transcript-segment-renderer, transcript-segment-view-model').length`
  in the page. If it's > 0 the transcript is present and the selector is at fault — never filter
  transcript panels on `target-id`, which is sometimes `null`. The panel can also open as a permanent
  empty shell (Chasing Pelagics, 2026-09-04, four retries) — that case is exactly why the library is
  now the primary path.

## Build Notes

Python 3 with a deliberately small dependency set — `matplotlib` + `numpy` for map rendering,
`ephem` for the moon, `reportlab` + `pillow` for the PDF. No web framework, no database, no API keys:
every source is public HTTP, so the Conditions engine runs headless and offline of any browser. That
separation is the core architectural decision — browser screenshots can't be written to disk on a
scheduled run, so maps are rendered from raw NOAA grids rather than captured from an interactive
chart tool.

Failure isolation is per-map: each fetch/draw pair is wrapped independently, so one dead source
degrades a single map instead of the section. `_urlopen` retries with backoff on 5xx/429 and fails
fast on permanent 4xx. Chlorophyll goes through an ordered dataset chain because ERDDAP dataset IDs
get retired without notice — the original 2 km product 404'd in July 2026 and silently cost a run
both water-color maps, which is why every map footer now prints the dataset and its computed lag.

## Update / Refresh Instructions

The weekly run is automated — the Cowork scheduled task fires Friday 9:02 AM Pacific (see
`SCHEDULE.md`) and needs Chrome open with the Claude in Chrome extension active for the landing and
long-range scrape (and the YouTube fallback). To refresh manually:

```bash
cd ~/Documents/Claude/Projects/"Weekly Saltwater Fishing Report"
pip install -r requirements.txt --break-system-packages -q   # first run in a fresh environment
/usr/bin/python3 tools/yt_transcript.py --days 7             # this week's YouTube transcripts, no Chrome
python3 conditions.py                                        # re-fetches live data every run
```

`conditions.py` is safe to re-run and overwrites the current date's maps and PDF in place;
`conditions_maps/` and `conditions_briefings/` self-prune beyond ~8 weeks. To change the monitored
sources edit `SKILL.md` (Parts 1–3); to move or add a Conditions region edit `REGIONS` in
`conditions.py` and mirror it in `SPEC-conditions.md`. After editing `SKILL.md`, sync the project
copy and the live scheduled copy at
`~/.claude/scheduled-tasks/weekly-saltwater-fishing-report/SKILL.md` — they have drifted before, with
the live copy ahead. **The two are identical except for config scrubbing:** the committed copy must
keep `<ALERT_EMAIL>`, `<SLACK_WORKSPACE>` and `<SLACK_CHANNEL_ID>` as placeholders (real values live
only in the scheduled copy and the gitignored `CONFIG.local.md`), so re-apply the scrub after any
copy from the live file into this repo.

---
_Last updated: 2026-07-31_
