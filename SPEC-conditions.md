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

## Outputs

**1. stdout** — the ready-to-paste Conditions Markdown (moon line, Core regions, Offshore banks, and
the `📄 Visual briefing` line), followed by a machine-readable footer:

```
<!-- BRIEFING
/Users/<you>/Documents/Claude/Projects/Weekly Saltwater Fishing Report/conditions_briefings/conditions_YYYYMMDD.pdf
-->
```

**2. `conditions_maps/*_YYYYMMDD.png`** — up to four maps: `socal_temp_break`, `baja_temp_break`,
`socal_water_color`, `baja_water_color`. Four is the healthy state; each map is produced
independently, so an upstream failure drops that one map and leaves the rest. Consumers must handle
a partial set and must never substitute an earlier date's render (`tools/dayone_attach.sh list` is
date-scoped for exactly this reason).

**3. `conditions_briefings/conditions_YYYYMMDD.pdf`** — one page of region tables + a page of
whichever maps were produced. Brand: navy `#2B4C7E`, teal `#2C7A6B`; SST uses `turbo`, chlorophyll a
blue→green ramp — both kept distinct from brand teal.

## Invariants

- **Numbers are authoritative and verbatim.** Consumers must not reformat, round differently, or
  add interpretation. Wind is **knots**.
- **Bank lines are optional** in the final report (drop if unfished), but the script always emits all.
- **Modeled label** stays on Baja offshore regions.
- **Graceful degrade:** a down map source → that map type is skipped and noted; a down region →
  that row is marked unavailable; the rest still print. None of these are alert conditions.
- **Pruning:** `conditions_maps/` and `conditions_briefings/` auto-delete files older than ~8 weeks.

## Config knobs

`PROJECT_MAC` (top of `conditions.py`) — the macOS project path used for the printed attachment/PDF
paths; override with the `FISHING_PROJECT_MAC` env var. `prune_old(days=56)` — retention window.
`REGIONS` — region list/coords. `build_maps()` bboxes/strides — map extent/resolution.
