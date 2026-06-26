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
lands in one Day One entry, with the Conditions maps delivered as a one-page PDF (because the Day
One connector can't embed image/PDF attachments — see BUILD-PLAN.md). Built for Ed, who reads the
report on Day One's desktop and mobile apps.

## Features

- **Conditions briefing header** — moon (phase + illumination), and per-region wind (knots), swell,
  and SST, with a tiered region list (core nearshore always; offshore banks only when fished).
- **Temperature-break maps** — NOAA MUR 1 km SST for SoCal and Baja, with contour breaks.
- **Water-color maps** — VIIRS+OLCI gap-filled chlorophyll (clean-blue vs. green-water edges).
- **One-page PDF briefing** — region tables + all four maps, brand-styled, dated, auto-pruned >8 wks.
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

## Configuration

Personal settings live in `SKILL.md` / `CLAUDE.md`: the alert **email**, the **Slack** workspace +
`#fishing-report-alerts` channel ID, and the Day One **journal** name ("Saltwater Fishing Journal").
On a public clone, replace these with your own (or scrub to placeholders and keep real values in a
gitignored `CONFIG.local.md`).

## Notes

- The Day One connector cannot embed attachments; the maps ship as a PDF you add via Day One's "+"
  button. The Slack success message includes the PDF path as the reminder.
- Conditions data is satellite/model-derived: NOAA MUR SST lags ~1 day, chlorophyll ~10 days, and
  Baja offshore has no buoys — useful for planning, not ground truth.
