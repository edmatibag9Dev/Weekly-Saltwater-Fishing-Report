# Weekly Saltwater Fishing Report — Build Plan & Technical Findings

*Owner: Ed · Conditions add-on drafted & built: 2026-06-26 · Status: live (first full run Jul 3, 2026)*

This documents the **Conditions briefing** add-on (wind / swell / SST / moon + maps) bolted onto the
pre-existing weekly report, and the hard findings that shaped it. The base report (YouTube + SD
landings + long-range scraping) predates this and is specified in SKILL.md Parts 1–3.

---

## 1. Decisions locked

| Decision | Choice | Why |
|---|---|---|
| Conditions numbers | **Open-Meteo Marine + Weather APIs** | Free, no key, global (covers deep Baja), JSON — won't break like a scrape. Verified live at Alijos Rocks & Tanner/Cortez. |
| Temp-break maps | **NOAA MUR 1 km SST** (`jplMURSST41`, CoastWatch ERDDAP) | Same SST source the paid tools use; rendered headlessly with matplotlib. |
| Water-color maps | **VIIRS+OLCI DINEOF gap-filled chlorophyll** (`noaacwNPPN20S3ASCIDINEOF2kmDaily`) | Raw daily VIIRS is ~60% cloud over SoCal in June; the L4 gap-filled blend gives clean coverage (~10-day science lag — fine for a slow signal). |
| Moon | **ephem** | Exact phase/illumination + next full/new, no network. |
| Map delivery | **One-page PDF** (reportlab) Ed adds via Day One "+" | The Day One connector can't embed attachments (see §3). PDF renders on desktop + mobile. |
| Region coverage | **Tiered** | Core nearshore always; offshore banks only when that week's reports mention them — avoids publishing model noise for water nobody fished. |
| Wind units | **Knots** | Marine standard. |
| Catalysst | **Not in the automated run** | Ed's richer interactive tool (AIS, chlorophyll, contours), but it's a login-gated DEV web app with no URL view-state and screenshots can't be saved to disk on the scheduled run. |

---

## 2. The core constraint that shaped the maps

> **The scheduled run cannot save browser screenshots to disk, and Day One attachments require a
> file on disk.**

So we do **not** screenshot Catalysst (or any map site). Instead `conditions.py` pulls the same NOAA
satellite grids Catalysst uses and renders real PNG files headlessly — then composes them into a PDF.
No Chrome, no login, no DEV-UI to break. This also makes the Conditions step independent of the
Chrome-dependent scraping: if a channel scrape hiccups, Conditions still produces.

```
Open-Meteo (numbers) ─┐
NOAA MUR SST ─────────┤→ conditions.py → text (verbatim) + conditions_YYYYMMDD.pdf
VIIRS+OLCI chl ───────┤                     │
ephem (moon) ─────────┘                     ▼
                                 Day One entry (text) + Ed drags PDF in via "+"
                                 Slack #fishing-report-alerts (path reminder)
```

---

## 3. The Day One attachment finding (the big one)

The original plan was to attach the map PNGs to the Day One entry. It doesn't work in this setup —
and we proved it methodically:

- `create_entry_with_attachments` returns "success" with the right **count**, but the images render
  as **blank grey placeholders**.
- Ruled out **format**: RGBA PNG and flattened RGB JPEG both failed.
- Ruled out **location**: attaching from the Documents project folder and from the app's outputs
  folder both failed.
- Ruled out **file validity**: the files open fine in Preview; macOS shows them correctly.
- **Decisive test:** the *same* file dragged into the entry via Day One's own "+" button renders
  perfectly (desktop + mobile). A connector-attached PDF also failed; a manually-added PDF works.

Conclusion: the connector's attach path never imports the bytes. **Workaround:** post text only, ship
maps as a PDF in `conditions_briefings/`, and Ed adds it with "+". The Slack success post carries the
PDF path (Slack doesn't make local `file://` paths clickable, so it's a copyable code span; on Mac,
Finder → Cmd+Shift+G → paste).

---

## 4. Guardrail: never improvise the Conditions

A dry run where `conditions.py` couldn't be found (the task was pointed at the wrong folder) exposed
a failure mode: the agent **hand-wrote** the Conditions section — wrong units (mph), single-snapshot
values, dropped regions, and an editorial "favorable for pelagics" line. SKILL.md and AGENTS.md now
forbid this: the numbers/moon must come from `conditions.py` stdout verbatim, and if the script can't
run the section becomes a single line — `🌊 Conditions — unavailable this run` — never a fabrication.

---

## 5. Regions (representative points)

SoCal Bight `32.9/-117.8` · Northern Baja `31.6/-116.9` · San Clemente–Catalina `33.1/-118.5` ·
Tanner-Cortez `32.5/-119.2` · Cedros/Guadalupe `28.2/-115.2` · Magdalena Bay `24.4/-112.2` ·
The Ridge `25.3/-114.6` · Alijos Rocks `24.95/-115.73`. Tune in `conditions.py > REGIONS`.

---

## 6. Open items / future

- If the Day One connector is fixed to embed attachments, flip back to auto-attaching the PDF (drop
  the manual "+" step). Track via the verification gates in AGENTS.md.
- Possible add: a chlorophyll/water-color legend tuned per-region; AIS fleet overlay is the one thing
  the free pipeline can't replicate (Catalysst-only).
