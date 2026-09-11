# SPEC — Conditions engine (`conditions.py`)

The data/interface contract for the weekly Conditions briefing. Anything that consumes Conditions
(the report assembler, the Slack reminder) depends on this. Keep it in sync with `conditions.py`.

## Inputs (all free, public, no key)

| Signal | Source | Dataset / endpoint |
|---|---|---|
| Wind (kt) | Open-Meteo Weather API | `wind_speed_10m_max`, `wind_gusts_10m_max`, `wind_direction_10m_dominant` |
| Swell (ft / s / dir) | Open-Meteo Marine API | `swell_wave_height_max`, `swell_wave_period_max`, `wave_direction_dominant` |
| SST (°F) | Open-Meteo Marine API (numbers) | `sea_surface_temperature_max/min` |
| Temp-break maps | NOAA CoastWatch ERDDAP | `jplMURSST41` (MUR 1 km SST, ~1-day lag) |
| Water-color maps | NOAA CoastWatch ERDDAP | `CHL_DATASETS` chain in `conditions.py`, first that answers: `noaacwNPPN20VIIRSDINEOFDaily` (NRT 9 km, ~2-day lag) → `noaacwNPPN20S3ASCIDINEOFDaily` (science, VIIRS+OLCI 9 km, ~11-day lag) → `noaacwNPPN20VIIRSSCIDINEOFDaily`. All DINEOF gap-filled. Dataset + lag are printed under each rendered map. **`noaacwNPPN20S3ASCIDINEOF2kmDaily` is retired (404) — do not reintroduce it.** |
| Moon | `ephem` | phase, % illumination, next full/new |
| Storm Watch | NOAA National Hurricane Center (NHC) | `CurrentStorms.json` (active storms + advisory links) → each storm's **TCM forecast/advisory text** (`/text/MIATCMEP<n>.shtml`: 12-hourly track points to 120 h, max wind, 34/50/64-kt radii) → the **TWO outlook text** (`/text/MIATWOEP.shtml`, 7-day formation odds). Images: `xgtwo/two_pac_7d0.png` (East Pacific 7-day outlook, 900×547) and `storm_graphics/EP<nn>/<ID>_5day_cone.png` (official 5-day cone, ~900×736), both plain PNGs at stable URLs derived from the storm ID. East Pacific basin only (`id` starts with `ep`). |

Forecast horizon: 7 days from run date. ERDDAP requests send a browser `User-Agent`.

## Regions (`REGIONS` in conditions.py)

`(name, lat, lon, tier)` — tier is `core` (always reported) or `bank` (reported only when that
week's reports mention it).

| Region | Lat | Lon | Tier |
|---|---|---|---|
| Southern California Bight | 32.9 | -117.8 | core |
| Northern Baja | 31.6 | -116.9 | core |
| San Clemente & Catalina | 33.1 | -118.5 | core |
| Tanner / Cortez Banks | 32.5 | -119.2 | bank |
| Cedros / Guadalupe | 28.2 | -115.2 | bank |
| Magdalena Bay | 24.4 | -112.2 | bank |
| The Ridge | 25.3 | -114.6 | bank |
| Alijos Rocks | 24.95 | -115.73 | bank |

## Storm Watch assessment (`storm_watch()` in conditions.py)

For every active East Pacific storm, the closest approach of any TCM track point (initial position +
forecast + outlook points) to each region's representative point is computed by great-circle distance
in nautical miles. Tiers, per region, then the storm takes the worst:

| Tier | Rule (constants at the top of the module) |
|---|---|
| **IMPACT** | closest approach − largest 34-kt wind radius at that point ≤ `STORM_IMPACT_NM` (60 nm) |
| **WATCH** | closest approach ≤ `STORM_WATCH_NM` (300 nm) |
| **MONITOR** | named storm exists, no region within 300 nm |
| clear | no active TS / HU / STS → "No named tropical storms or hurricanes in the East Pacific this week." |

Named storms (TS, HU, STS) always print; a depression (TD) prints only when it reaches WATCH/IMPACT.
A **Formation outlook** line prints for each TWO paragraph whose 7-day chance is ≥
`STORM_FORMATION_MIN_PCT` (60%). Thresholds are Ed's report conventions, not NHC guidance; NHC's
own day-4 track error (~100 nm) is stated in the block. Every storm line links its NHC page.

## Outputs

**1. stdout** — the ready-to-paste Conditions Markdown: moon line, Core regions, Offshore banks, the
`📄 Visual briefing` line, then one `_caption_` + `[{attachment}]` pair per produced Conditions map,
the **Storm Watch** block, and one caption + `[{attachment}]` pair per storm image (7-day outlook
first, then a 5-day cone per named storm). Two machine-readable footers follow:

```
<!-- BRIEFING
/Users/<you>/Documents/Claude/Projects/Weekly Saltwater Fishing Report/conditions_briefings/conditions_YYYYMMDD.pdf
-->
<!-- ATTACHMENTS
/Users/<you>/Library/Group Containers/5U8NS4GX82.dayoneapp2/Data/Documents/CLI-Inbox/socal_temp_break_YYYYMMDD.png
… one line per [{attachment}] above, same order …
-->
```

`[{attachment}]` is the Day One CLI's positional placeholder: the run passes the ATTACHMENTS list
verbatim (same order) as `attachments=` to `create_journal_entry`, and the CLI drops image *n* where
placeholder *n* sits. Placeholder count == list length by construction. The list is empty (and no
placeholders are emitted) on a Mac without the Day One group container.

**2. `conditions_maps/*_YYYYMMDD.png`** — up to four maps: `socal_temp_break`, `baja_temp_break`,
`socal_water_color`, `baja_water_color`, plus `storm_outlook` (always attempted) and
`storm_<name>` (one per named storm, max 5). Four Conditions maps + the outlook is the healthy state;
each image is produced independently, so an upstream failure drops that one image and leaves the
rest. Consumers must handle a partial set and must never substitute an earlier date's render
(`tools/dayone_attach.sh list` is date-scoped for exactly this reason).
`conditions_maps/attachments_YYYYMMDD.txt` is the ordered inbox manifest (same content as the
ATTACHMENTS footer) that `tools/dayone_attach.sh inbox` / `trigger` read.

**2b. Day One inbox copies** — every produced image is also copied to
`~/Library/Group Containers/5U8NS4GX82.dayoneapp2/Data/Documents/CLI-Inbox/` (override:
`DAYONE_INBOX`). Day One is the sandboxed App Store build and its attachment import can only read
files inside its own group container; files elsewhere yield blank placeholders. The import is lazy —
bytes are read the first time the entry is displayed — so the inbox copies must outlive the run
(they are pruned with the maps after ~8 weeks).

**3. `conditions_briefings/conditions_YYYYMMDD.pdf`** — one page of region tables, a page of
whichever maps were produced, and a Storm Watch page (storm table, assessment lines, 7-day outlook,
cones). Brand: navy `#2B4C7E`, teal `#2C7A6B`; SST uses `turbo`, chlorophyll a
blue→green ramp — both kept distinct from brand teal.

## Invariants

- **Numbers are authoritative and verbatim.** Consumers must not reformat, round differently, or
  add interpretation. Wind is **knots**.
- **Bank lines are optional** in the final report (drop if unfished), but the script always emits all.
- **Modeled label** stays on Baja offshore regions.
- **Graceful degrade:** a down map source → that map type is skipped and noted; a down region →
  that row is marked unavailable; NHC unreachable → the block prints as
  `**⛈️ Storm Watch** — unavailable this run (reason)` and the text links still stand; a missing
  storm image → its placeholder is simply not emitted. None of these are alert conditions.
- **Storm Watch is verbatim too.** The tiers, distances and the formation line come from the script;
  the run must not re-grade a storm or add its own storm commentary.
- **Pruning:** `conditions_maps/` and `conditions_briefings/` auto-delete files older than ~8 weeks.

## Config knobs

`PROJECT_MAC` (top of `conditions.py`) — the macOS project path used for the printed attachment/PDF
paths; override with the `FISHING_PROJECT_MAC` env var. `prune_old(days=56)` — retention window.
`REGIONS` — region list/coords. `build_maps()` bboxes/strides — map extent/resolution.
`STORM_IMPACT_NM` / `STORM_WATCH_NM` / `STORM_FORMATION_MIN_PCT` / `STORM_MAX_CONES` — Storm Watch
tiers and caps. `DAYONE_INBOX` env — where the attachable copies go.
