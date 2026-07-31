# Weekly Saltwater Fishing Report

An automated weekly fishing-intelligence report for Southern California & Baja. Every Friday it
compiles YouTube fishing intel, San Diego landing fish counts, and long-range boat reports into a
single **Day One** journal entry — led by a forward-looking **Conditions** briefing (wind, swell,
SST, moon, and temperature-break + water-color maps) built entirely from free public data.

## Overview / Purpose

This answers "what's been biting, where, and what will the water be doing this week?" A Cowork
scheduled task (Friday 9:02 AM Pacific) scrapes six YouTube channels, four San Diego landings, and
LongRangeSportfishing.net through the Chrome extension, then runs a headless **Conditions engine**
(`conditions.py`) that pulls live numbers and renders maps with no Chrome and no logins. Everything
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
| `tools/dayone_attach.sh` | Embeds the run's maps into the saved Day One entry (clipboard paste via osascript) |
| `requirements.txt` | Python deps for `conditions.py` |
| `conditions_maps/`, `conditions_briefings/` | Generated outputs (gitignored) |

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
| 6 YouTube channels · [sandiegofishreports.com](https://www.sandiegofishreports.com/) · [longrangesportfishing.net](https://www.longrangesportfishing.net/fishreports.php) | Bite intel, dock counts, boat reports | Scraped weekly via Chrome |

All sources are public HTTP with no keys or logins.

## Known Limitations / Workarounds

- The Day One connector cannot embed attachments, so maps are embedded by pasting image data into
  the saved entry via `tools/dayone_attach.sh` (`paste` / `clip_paste`). Those subcommands send the
  keystroke themselves through `osascript`, so the step runs from Bash and needs **no computer-use
  grant** — which matters because computer-use access cannot be approved during a scheduled run. The
  one prerequisite is macOS **Accessibility** permission for the host app. If the paste fails, the
  run still posts and the Slack message carries the PDF path as a manual fallback.
- Conditions data is satellite/model-derived: NOAA MUR SST lags ~1 day, chlorophyll ~2 days on the
  near-real-time product (~11 on the science-quality backstops), and Baja offshore has no buoys —
  useful for planning, not ground truth.
- Embed only the current run's maps. `dayone_attach.sh list` is date-scoped and reports
  `MISSING:<file>` on stderr; fewer than four maps is normal when a source is down.

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
- **"Transcript extraction failed."** Before trusting it, check
  `document.querySelectorAll('ytd-transcript-segment-renderer, transcript-segment-view-model').length`
  in the page. If it's > 0 the transcript is present and the selector is at fault — never filter
  transcript panels on `target-id`, which is sometimes `null`.

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
`SCHEDULE.md`) and needs Chrome open with the Claude in Chrome extension active. To refresh manually:

```bash
cd ~/Documents/Claude/Projects/"Weekly Saltwater Fishing Report"
pip install -r requirements.txt --break-system-packages -q   # first run in a fresh environment
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
