# AGENTS.md — guide for AI agents working in this repo

This file is the canonical entry point for any AI agent (Claude Code, Cowork, Codex, etc.)
asked to **use, reference, extend, or rebuild** this project. Read it before acting.

## What this repo is

A local-first **Weekly Saltwater Fishing Report** for Southern California & Baja waters. Every
Friday at 9:02 AM Pacific a Cowork scheduled task compiles fishing intelligence into a single
**Day One** journal entry: it pulls YouTube transcripts headlessly (`tools/yt_transcript.py`,
Chrome only as a per-video fallback), scrapes San Diego landing fish counts and long-range boat
reports via the Chrome extension, and renders a forward-looking **Conditions** briefing (wind /
swell / SST / moon + temperature-break & water-color maps + a **Storm Watch** on named East Pacific
tropical storms / hurricanes from NOAA's National Hurricane Center) from free public APIs.

Design in one line: **6 YouTube channels (headless, Chrome fallback) + 4 SD landings + long-range
reports (Chrome) + a headless Conditions engine (no Chrome) → one Day One entry, with the maps and
NHC storm graphics attached inline at save time (and bundled in a PDF).**

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
| `conditions.py` | yes | The Conditions engine — numbers, maps, moon, Storm Watch (NOAA NHC), Day One inbox staging, PDF. No Chrome, no login. |
| `requirements.txt` | yes | Python deps for `conditions.py`. |
| `SETUP.md` | yes | Connector setup / troubleshooting. |
| `samples/conditions_sample.txt` | yes | Committed sample of `conditions.py` stdout (a real Conditions briefing text) so the repo previews without the gitignored live output. |
| `samples/conditions_sample.pdf` | yes | Committed sample one-page Conditions briefing PDF (temp-break + water-color maps) — reference for what the live `conditions_briefings/` PDFs look like. |
| `tools/yt_transcript.py` | yes | Headless YouTube step: channel Atom feeds → drop Shorts (`/shorts/<id>` HEAD 200 vs 303) → newest captioned upload in window → `youtube_transcript_api` → `youtube_transcripts/<stamp>/<key>.txt` + `manifest.json`, one status line per channel. Run with `/usr/bin/python3`. |
| `tools/dayone_attach.sh` | yes | Shell helper for the image step: `inbox` (this run's attachable paths), `trigger <uuid>` (open the entry so Day One performs its lazy import, poll the photo count), `list`, `count`. The old clipboard-paste subcommands are deprecated (exit 3). |
| `conditions_maps/` | **no (gitignored)** | Rendered map + storm PNGs and `attachments_<stamp>.txt` (timestamped; auto-pruned >8 wks). |
| `conditions_briefings/` | **no (gitignored)** | Dated PDF briefings generated each run. |
| `youtube_transcripts/` | **no (gitignored)** | Per-run transcript pulls + manifest (third-party content; auto-pruned >8 wks). |
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

📄 **Visual briefing:** 4 temp-break + water-color maps below; ... PDF ...:
`<mac path>/conditions_briefings/conditions_YYYYMMDD.pdf`

_<caption>_
[{attachment}]            ← one pair per produced Conditions map

**⛈️ Storm Watch** _(NOAA National Hurricane Center · East Pacific · advisory <time>; checked <time>)_
- **Tropical Storm <Name>** (<kt> kt) — <pos>, moving <dir> <kt> kt · closest approach <region> ~<nm> nm (<day>) · 🟢 MONITOR | 🟠 **WATCH** | 🔴 **IMPACT** … · [NHC page](url)
- **Formation outlook:** <pct>% chance through 7 days … (only when ≥ 60%)
- 7-day outlook: [NHC East Pacific graphical outlook](url)
_Tiers: …_

_Tropical / Hurricane — NOAA NHC East Pacific 7-day outlook_
[{attachment}]            ← always first in the storm set
_<Storm> — NHC 5-day forecast cone_
[{attachment}]            ← one per named storm

<!-- BRIEFING
<mac path to the PDF>
-->
<!-- ATTACHMENTS
<inbox path>              ← one line per [{attachment}] above, same order
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
  the Slack reminder. The `<!-- ATTACHMENTS -->` footer is the ordered list to pass **verbatim** as
  `attachments=` when the entry is created; never edit, reorder, or re-point it (the paths are inside
  Day One's group container on purpose — see below). Never delete a `[{attachment}]` line.
- **Storm Watch is script output too.** Do not re-grade a storm, change a tier, or add storm
  commentary; the tiers are defined in SPEC-conditions.md.

## How the run works

1. **YouTube (no Chrome).** `/usr/bin/python3 tools/yt_transcript.py --days 7` — one status line
   per channel; only `FETCH_FAILED` / `FEED_FAILED` channels fall back to the Chrome UI method kept in
   SKILL.md Part 1. Then **scrape (Chrome)** the 4 SD landing fish-count archives and
   LongRangeSportfishing.net — SKILL.md Parts 2–3. Chrome open + signed in is still required.
2. **Conditions (no Chrome).** `pip install -r requirements.txt --break-system-packages -q`, then
   `python3 conditions.py`. It pulls wind/swell/SST from Open-Meteo, renders temp-break maps from
   NOAA MUR and water-color maps from VIIRS+OLCI chlorophyll, pulls the NHC storm feeds and graphics,
   computes the moon with `ephem`, copies every image into Day One's inbox, and compiles the **PDF**
   into `conditions_briefings/`. It prints the report text + the PDF path + the attachment list.
3. **Assemble + post.** Paste the Conditions text at the top (placeholders included), fill the catch
   sections, and save with `mcp__dayone__create_journal_entry(attachments=<ATTACHMENTS list>)`. Then
   `bash tools/dayone_attach.sh trigger <uuid>` — see the attachment mechanics below.
4. **Notify.** Post a success summary to Slack (`#fishing-report-alerts`) including the PDF path as a
   reminder for Ed to drop the PDF into the entry. On error, alert via Gmail + Slack (Apple Notes
   fallback). See SKILL.md.

## The attachment mechanics (important — root-caused 2026-09-11)

Day One on this Mac is the **sandboxed App Store build** (`com.apple.security.app-sandbox` on both
the app and the bundled `dayone` CLI). Two facts follow, both verified 2026-09-11:
1. The attachment import can only read files **inside the app's group container**
   (`~/Library/Group Containers/5U8NS4GX82.dayoneapp2/…`). A path under `/tmp`, `~/Documents`, or
   the project folder records a moment but never imports the bytes → the "blank placeholder" that
   was misdiagnosed in June as "the connector is broken".
2. The import is **lazy**: the bytes are read the first time the entry is displayed. A just-created
   entry shows `ZHASDATA=0` until something opens it; `open "dayone://edit?entryId=<uuid>"` completes
   the import in ~5 s.

Therefore `conditions.py` copies every image to `…/Data/Documents/CLI-Inbox/`, the run attaches those
paths (positioned by `[{attachment}]`), and `tools/dayone_attach.sh trigger <uuid>` opens the entry
and polls `count` until it matches. The PDF remains a portable fallback.

**Dead ends — do not retry them:** clipboard paste via System Events keystrokes, the Edit ▸ Paste
menu item, and hardware-level CGEvent Cmd+V all reach Day One but its editor ignores them (0 of 4 on
every scheduled run 2026-07-31 → 2026-09-11). `dayone://post?imageClipboard=1` creates the entry
without the image. The URL-scheme and paste paths are documented in CHANGELOG 2026-09-11.

## How to extend

- **Add/retune a region:** edit the `REGIONS` list in `conditions.py` (name, lat, lon, tier). Add a
  matching marker to `_SOCAL_MARKERS` / `_BAJA_MARKERS` and, if it shifts the map frame, the bbox in
  `build_maps()`. Update SPEC-conditions.md.
- **Add a YouTube channel:** add a `(key, name, handle, channel_id)` row to `CHANNELS` in
  `tools/yt_transcript.py` (leave `channel_id` blank and it is resolved from the handle at run time),
  then edit SKILL.md Part 1 and CLAUDE.md's monitored list, and re-sync the live task (SCHEDULE.md).
- **Add an SD landing:** edit SKILL.md Part 2 (and CLAUDE.md), then re-sync the live task.
- **Swap a data source:** numbers = Open-Meteo; temp-break = NOAA MUR (`jplMURSST41`, served only by
  `coastwatch.pfeg.noaa.gov`); water-color = the `CHL_DATASETS` fallback chain in `conditions.py`
  (NRT 9 km first, science 9 km as backstops). All via public HTTP — no keys. Keep the
  verbatim/no-improvise rule. **ERDDAP dataset IDs get retired without notice** — the old 2 km
  `noaacwNPPN20S3ASCIDINEOF2kmDaily` began 404ing and silently cost a run both water-color maps.
  Prefer extending the chain over replacing it, and check a missing map against the live catalog
  (`/erddap/search/index.json?searchFor=…`) before writing it off as a transient outage.
- **Change the PDF look:** `build_pdf()` in `conditions.py` (brand: navy `#2B4C7E`, teal `#2C7A6B`;
  keep SST/chlorophyll data palettes separate from brand teal).
- **Retune Storm Watch:** `STORM_IMPACT_NM`, `STORM_WATCH_NM`, `STORM_FORMATION_MIN_PCT`,
  `STORM_MAX_CONES` at the top of the storm section in `conditions.py`; basin filter is the `ep`
  prefix on the NHC storm id. Cone URL pattern: `storm_graphics/EP<nn>/<ID>_5day_cone.png` (verified
  on Norbert EP142026 only — if a second storm's cone 404s, check the storm's graphics page).

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
4. Maps render for the current date stamp and old files >8 weeks are pruned. **All four** (2
   temp-break + 2 water-color) is the healthy state and what a normal run must produce — but fewer is
   a legitimate degraded result when an upstream source is down, so treat a shortfall as a signal to
   investigate, not an automatic fail. Confirm which succeeded rather than counting files:
   `python3 -c "import conditions as c; print(c.build_maps())"` reports a path per map or the
   exception that killed it. A map that fails two runs running is a real defect — check whether the
   ERDDAP dataset ID was retired (the 2 km chlorophyll product was, in July 2026) before assuming a
   transient outage.
5. The Day One save passes the `<!-- ATTACHMENTS -->` list verbatim as `attachments=` to
   `create_journal_entry`; `[{attachment}]` count in the text equals the list length; then
   `bash tools/dayone_attach.sh trigger <uuid>` prints `EMBEDDED=N/N` and exits 0.
6. `/usr/bin/python3 tools/yt_transcript.py --only dancing_on_water` exits 0 and prints a status line.
   (That channel has had no upload in months, so the check makes zero transcript requests and cannot
   contribute to an IP block; a full 6-channel run is the real test but costs 5–8 fetches.)
7. Storm Watch: stdout contains `**⛈️ Storm Watch**`; `conditions_maps/storm_outlook_<stamp>.png` is a
   real PNG; with a named storm active, `storm_<name>_<stamp>.png` exists and the storm line carries a
   tier and an NHC link. `conditions_maps/attachments_<stamp>.txt` lists every image in entry order.
   A quick offline check of the track parser: `python3 -c "import conditions as c; print(c._assess(c._parse_tcm(open('samples/tcm_sample.txt').read()))[:3])"`.

---

## What to Stage — Never Commit Blindly

Staging is part of the commit, not a detail beneath it. A commit records what you
staged, so an unconditional stage records whatever state the working tree happens
to be in — including damage you did not cause and did not notice.

### Rules

- **Stage named paths.** `git add <path> <path>` — only the files your change
  actually touched. You should be able to say why each one is in the commit.
- **Never `git add -A`, `git add .`, `git add --all`, or `git commit -a`** in a
  repository that already has history. Use them only to bootstrap a fresh
  `git init`, and verify the staged list before that first commit.
- **Check for deletions before every commit:**

  ```
  git diff --cached --name-status --diff-filter=D
  ```

  If that prints anything you did not deliberately delete, STOP. Unstage with
  `git reset`, find out why the file is missing, and restore it. Do not commit
  the removal.
- **A file missing from the working tree is not a change.** It is a filesystem,
  sync-client, or tooling problem. Committing its deletion converts a recoverable
  accident into recorded history and destroys the git copy that would have
  restored it.
- **Untracked is not protected.** A file that was never committed has no git copy
  at all. If a working file matters, commit it or ignore it deliberately — never
  leave it untracked by accident.

### Staging self-check

- [ ] Staged named paths only — no `-A`, no `.`, no `-a`
- [ ] `git diff --cached --name-status --diff-filter=D` shows nothing unintended
- [ ] Every staged path belongs to the change described in the commit message

### Why this rule exists

On 2026-08-30, commit `3df1d05` in the ai-briefing repo — a routine data commit —
was staged unconditionally while two files were missing from the working tree. A
two-way sync client had deleted them nine days earlier. The commit recorded both
deletions, removing the last recoverable copies from git and leaving the sync
client's quarantine folder as the only source. They were recovered, but only
because that quarantine had not yet been purged on its retention timer.

The same pattern nearly caused a data leak once before: an untracked `reports/`
folder holding local absolute paths and an email address sat in a public repo,
where any `git add .` would have swept it into a public commit.

Unconditional staging fails in both directions. It commits what should never be
published, and it deletes what should never be lost.
