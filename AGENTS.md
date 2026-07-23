# AGENTS.md — guide for AI agents working in this repo

This file is the canonical entry point for any AI agent (Claude Code, Cowork, Codex, etc.)
asked to **use, reference, extend, or rebuild** this project. Read it before acting.

## What this repo is

A local-first **Weekly Saltwater Fishing Report** for Southern California & Baja waters. Every
Friday at 9:02 AM Pacific a Cowork scheduled task compiles fishing intelligence into a single
**Day One** journal entry: it scrapes YouTube transcripts, San Diego landing fish counts, and
long-range boat reports (via the Chrome extension), and renders a forward-looking **Conditions**
briefing (wind / swell / SST / moon + temperature-break & water-color maps) from free public APIs.

Design in one line: **6 YouTube channels + 4 SD landings + long-range reports (Chrome) +
a headless Conditions engine (no Chrome) → one Day One entry, with the Conditions maps delivered
as a one-page PDF.**

The Conditions section sits at the **top** of the report as a briefing header that frames the
retrospective catch intel below it.

## File map

| Path | Committed? | Purpose |
|---|---|---|
| `AGENTS.md` | yes | This guide. |
| `README.md` | yes | Human quickstart + command reference. |
| `llms.txt` | yes | Machine-readable index of these files. |
| `CLAUDE.md` | yes | Project instructions: connectors, sources, known behaviors. |
| `SKILL.md` | yes | The full scheduled-task prompt (sources → format → notifications → alerts). Kept in sync with the live Cowork task. |
| `BUILD-PLAN.md` | yes | Architecture, decisions, and the hard findings from the build. |
| `SPEC-conditions.md` | yes | The Conditions data contract — regions, coords, sources, stdout format, PDF. |
| `SCHEDULE.md` | yes | How the weekly Cowork scheduled task is configured/edited. |
| `CHANGELOG.md` | yes | Notable changes (Keep a Changelog). |
| `CONTRIBUTING.md` | yes | Ed's global commit + doc standards. |
| `.gitignore` | yes | Excludes generated output + real/personal data (maps, briefings, archives, `CONFIG.local.md`, `__pycache__`); keeps `samples/` committed. |
| `conditions.py` | yes | The Conditions engine — numbers, maps, moon, PDF. No Chrome, no login. |
| `requirements.txt` | yes | Python deps for `conditions.py`. |
| `SETUP.md` | yes | Connector setup / troubleshooting. |
| `samples/conditions_sample.txt` | yes | Committed sample of `conditions.py` stdout (a real Conditions briefing text) so the repo previews without the gitignored live output. |
| `samples/conditions_sample.pdf` | yes | Committed sample one-page Conditions briefing PDF (temp-break + water-color maps) — reference for what the live `conditions_briefings/` PDFs look like. |
| `tools/dayone_attach.sh` | yes | Shell helper that pastes the Conditions map PNGs into a Day One entry via clipboard/System Events, working around the broken Day One connector attachment path. |
| `conditions_maps/` | **no (gitignored)** | Rendered map PNGs (timestamped; auto-pruned >8 wks). |
| `conditions_briefings/` | **no (gitignored)** | Dated PDF briefings generated each run. |
| `past-reports/` | **no (gitignored)** | Optional local archive of exported entries. |

## The Conditions data contract (`conditions.py` stdout)

`conditions.py` is the single source of truth for the Conditions section. The run pastes its
stdout **verbatim**. The shape is stable:

```
## 🌊 Conditions — Week of <Mon D – Mon D, YYYY>

🌙 **Moon:** <phase / event> · <lo>–<hi>% illuminated this week. <one-line bite note>

**Core regions**
- **Southern California Bight** — Wind <dir> <lo>–<hi> kt, gusts <g> · Swell <lo>–<hi> ft <dir> @ <p>s · SST <lo>–<hi>°F
- ... (Northern Baja, San Clemente & Catalina)

**Offshore banks** _(modeled — include a line ONLY if this week's reports mention that area)_
- **Tanner / Cortez Banks** — Wind ... · Swell ... · SST ...
- ... (Cedros/Guadalupe, Magdalena Bay, The Ridge, Alijos Rocks)

📄 **Visual briefing:** the 4 ... maps are in a one-page PDF saved to the project folder:
`<mac path>/conditions_briefings/conditions_YYYYMMDD.pdf`

<!-- BRIEFING
<mac path to the PDF>
-->
```

Rules an agent must preserve:
- **Never hand-write, estimate, reformat, or editorialize** the moon line or any wind / swell / SST
  value. They come from `conditions.py` only. If the script can't run, write
  `🌊 Conditions — unavailable this run` — do NOT improvise the section. (A past run that used mph,
  single-snapshot values, and "favorable for pelagics" was an incorrect improvisation.)
- **Wind is in knots.** Baja offshore regions are MODELED (no buoys) and stay tagged "modeled".
- **Tiering:** always include the three Core regions. Include an Offshore-bank line ONLY if that
  week's YouTube/long-range reports actually mention that area; otherwise delete the line.
- The `<!-- BRIEFING -->` footer carries the PDF's macOS path — capture it for the Day One text and
  the Slack reminder.

## How the run works

1. **Scrape (Chrome).** YouTube transcripts (6 channels), 4 SD landing fish-count archives, and
   LongRangeSportfishing.net — see SKILL.md Parts 1–3. Requires Chrome open + signed in.
2. **Conditions (no Chrome).** `pip install -r requirements.txt --break-system-packages -q`, then
   `python3 conditions.py`. It pulls wind/swell/SST from Open-Meteo, renders temp-break maps from
   NOAA MUR and water-color maps from VIIRS+OLCI chlorophyll, computes the moon with `ephem`, and
   compiles a one-page **PDF** into `conditions_briefings/`. It prints the report text + the PDF path.
3. **Assemble + post.** Paste the Conditions text at the top, fill the catch sections, and save with
   `mcp__dayone__create_journal_entry` (TEXT ONLY — see the attachment caveat below).
4. **Notify.** Post a success summary to Slack (`#fishing-report-alerts`) including the PDF path as a
   reminder for Ed to drop the PDF into the entry. On error, alert via Gmail + Slack (Apple Notes
   fallback). See SKILL.md.

## The attachment caveat (important)

The Day One connector's attachment function is **broken in this setup** — `create_entry_with_attachments`
records the count but never embeds the bytes, so attached PNG/JPG/PDF render as blank placeholders.
Verified across image formats (RGBA PNG, RGB JPEG), file locations, and PDF. A file dragged in
through Day One's own "+" button renders fine. Therefore:
- The job posts the entry as **text only** and never attaches via the connector.
- Maps ship as the **PDF** in `conditions_briefings/`; Ed adds it manually via "+" (renders on
  desktop + mobile). The Slack success post repeats the PDF path.

## How to extend

- **Add/retune a region:** edit the `REGIONS` list in `conditions.py` (name, lat, lon, tier). Add a
  matching marker to `_SOCAL_MARKERS` / `_BAJA_MARKERS` and, if it shifts the map frame, the bbox in
  `build_maps()`. Update SPEC-conditions.md.
- **Add a YouTube channel / SD landing:** edit SKILL.md Parts 1–2 (and CLAUDE.md's monitored lists),
  then re-sync the live task (SCHEDULE.md).
- **Swap a data source:** numbers = Open-Meteo; temp-break = NOAA MUR (`jplMURSST41`); water-color =
  `noaacwNPPN20S3ASCIDINEOF2kmDaily`. All via public HTTP — no keys. Keep the verbatim/no-improvise rule.
- **Change the PDF look:** `build_pdf()` in `conditions.py` (brand: navy `#2B4C7E`, teal `#2C7A6B`;
  keep SST/chlorophyll data palettes separate from brand teal).

## Privacy — hard rules

- This repo is **public**. `SKILL.md`/`CLAUDE.md` may carry Ed's alert email and Slack channel ID;
  scrub them to placeholders (and keep real values in a gitignored `CONFIG.local.md`) if that exposure
  isn't wanted. Never commit tokens, passwords, or API keys.
- Never commit the gitignored folders (`conditions_maps/`, `conditions_briefings/`, `past-reports/`).
- The Conditions data is public weather/satellite data — safe to share; sample PDFs are fine to commit.

## Verification gates (run before declaring a change done)
1. `python3 conditions.py` exits 0, prints the Conditions text, and writes a non-empty PDF to
   `conditions_briefings/conditions_YYYYMMDD.pdf`.
2. Wind is in knots; every region row has wind + swell + SST; Baja offshore rows say "modeled".
3. The `<!-- BRIEFING -->` footer contains a valid macOS PDF path.
4. The four maps render (2 temp-break + 2 water-color) and old files >8 weeks are pruned.
5. The Day One save uses `create_journal_entry` (text), NOT `create_entry_with_attachments`.
