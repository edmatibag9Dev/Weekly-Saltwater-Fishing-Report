# Changelog

All notable changes to the Weekly Saltwater Fishing Report are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); dates are America/Los_Angeles.
Generated outputs (`conditions_maps/`, `conditions_briefings/`, `past-reports/`) are gitignored and
never committed.

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
