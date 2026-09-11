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
| Water-color maps | **DINEOF gap-filled chlorophyll**, `CHL_DATASETS` chain (NRT 9 km → science 9 km) | Raw daily VIIRS is ~60% cloud over SoCal in June; the L4 gap-filled blend gives clean coverage. Originally `noaacwNPPN20S3ASCIDINEOF2kmDaily` (2 km, ~10-day lag) — **retired by NOAA 2026-07, now 404** — replaced 2026-07-31 by a fallback chain leading with the near-real-time 9 km product (~2-day lag). |
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

## 3. The Day One attachment finding (the big one) — SUPERSEDED 2026-09-11

**2026-09-11 root cause:** Day One is the sandboxed App Store build. Its attachment import can only
read files inside the app's group container, and it imports lazily when the entry is first
displayed. Every June test attached from `/tmp` or `~/Documents`, so the moment was recorded and the
bytes never read. Attaching the same file from
`~/Library/Group Containers/5U8NS4GX82.dayoneapp2/Data/Documents/CLI-Inbox/` and then opening the
entry (`dayone://edit?entryId=…`) imports it in ~5 s — 6/6 verified, placeholders position the
images inline. The clipboard-paste workaround that replaced the PDF-drag in June never embedded a map
on a scheduled run (0/4 from 2026-07-31 to 2026-09-11) and is now deprecated. See CHANGELOG
2026-09-11 and AGENTS.md "attachment mechanics". The June record is kept below for history.

The original plan was to attach the map PNGs to the Day One entry. It appeared not to work — and we
"proved" it methodically, but every test shared the one variable that mattered (file location):

- `create_entry_with_attachments` returns "success" with the right **count**, but the images render
  as **blank grey placeholders**.
- Ruled out **format**: RGBA PNG and flattened RGB JPEG both failed.
- Ruled out **location**: attaching from the Documents project folder and from the app's outputs
  folder both failed.
- Ruled out **file validity**: the files open fine in Preview; macOS shows them correctly.
- **Decisive test:** the *same* file dragged into the entry via Day One's own "+" button renders
  perfectly (desktop + mobile). A connector-attached PDF also failed; a manually-added PDF works.

June conclusion (now known to be wrong): "the connector's attach path never imports the bytes."
What was actually true: it never imports bytes *from outside the sandbox*. The PDF remains the
portable fallback and its path still rides in the Slack post.

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

## 7. The YouTube transcript finding (2026-09-09)

The Chrome-driven transcript scrape was the least reliable step in the pipeline and each fix
(2026-07-09 dual-panel reader, 2026-07-31 content-based panel selection) narrowed the failure
without removing it. On 2026-09-04 a video with 17 published caption tracks opened a transcript
panel that never populated through four retries including reload and close/reopen, and the
in-page caption-URL fallback returned an empty body because YouTube now requires a Proof-of-Origin
token on that endpoint. The library `youtube_transcript_api` (1.2.4) fetched the same video's full
16,936-character transcript in one call, so it is now the primary path and the Chrome procedure is
the per-video fallback.

Findings from building `tools/yt_transcript.py`:

- **Channel Atom feeds** (`youtube.com/feeds/videos.xml?channel_id=…`) give exact ISO publish
  timestamps and need no browser, but they **list Shorts without flagging them**. Three of
  Fisherman's Landing's six newest uploads were 20-second clips with no captions; the first build
  selected one as "the weekly report". A HEAD on `youtube.com/shorts/<id>` answers 200 for a Short
  and 303 for a normal video (3/3 consistent on four test videos); oEmbed dimensions are not usable
  because every video reports 200×113.
- **YouTube rate-limits the library by IP** (`IpBlocked`). Triggered once during testing at
  roughly 20 fetches in 10 minutes; a weekly run makes 5–8. The script stops fetching at the first
  block instead of retrying, and the Chrome fallback was verified to still pull a transcript from
  the same IP while the library was blocked — the browser session is authenticated, the library is
  not. Block duration is unknown.
- **Interpreter pinning matters.** The library is installed for `/usr/bin/python3` (3.9) and the
  python.org 3.14, not Homebrew's. Under launchd `PATH` resolves `python3` to `/usr/bin/python3`;
  in an interactive shell it resolves to 3.14. The script is invoked with the absolute path.
- **A same-day stale file can lie.** A run that succeeds and a later run that is blocked leave a
  `.txt` beside a `FETCH_FAILED` manifest. Any non-OK status now deletes that channel's file, so the
  status line, not the file, is the record.

