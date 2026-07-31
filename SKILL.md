---
name: weekly-saltwater-fishing-report
description: Every Friday 9:00 AM — weekly saltwater fishing report: conditions briefing + SoCal/Baja YouTube transcripts + 4 SD landing fish counts + long range boat reports → Day One
---

You are compiling a weekly saltwater fishing report for SoCal and Baja waters. Your job is to:
1. Visit the YouTube channels below, find the most recent video posted within the last 7 days, extract transcripts, and pull fishing intel.
2. Visit the San Diego Fish Reports landing pages below, pull the last 7 days of fish count data from the monthly archive calendar.
3. Visit LongRangeSportfishing.net and extract all fish reports from the last 7 days, organized by boat.
4. Generate the weekly **Conditions** section (wind / swell / SST / moon + a PDF map briefing) by running `conditions.py` — see PART 4. This step uses no Chrome.

All data is combined into a single structured Day One journal entry.

---

## PART 1 — YouTube Channels to Check

1. BDoutdoors — https://www.youtube.com/@bdoutdoorsdotcom-m4p
2. Friedman Adventures Podcast — https://www.youtube.com/@FriedmanAdventuresPodcast
3. Dancing on Water — https://www.youtube.com/@DancingonWater1203
4. Arthur Pereira — https://www.youtube.com/@ArthurPereira1974
5. Chasing Pelagics — https://www.youtube.com/@ChasingPelagics
6. Fisherman's Landing — https://www.youtube.com/@fishermanslanding

### Steps for Each YouTube Channel

1. Navigate to the channel's Videos page (append /videos to the channel URL).
2. Identify the most recent video published within the last 7 days. Check the metadata timestamps (e.g. "1 day ago", "3 days ago"). If no new video was posted this week, skip that channel and note it in the report.
3. Open the video page.
4. Extract the full transcript. **Do NOT use a bare JavaScript `.click()`, and do NOT assume the classic transcript panel.** YouTube now serves two transcript-panel variants, bucketed **per video** (so within one run some videos use one and some use the other), and a synthetic `.click()` frequently fails to fire YouTube's transcript fetch — this is the cause of the intermittent "transcript unavailable" false negatives. Follow this exact sequence:

   **a. Confirm captions actually exist first (genuine-vs-failed gate).** Read the player caption tracks:
   ```js
   (window.ytInitialPlayerResponse?.captions?.playerCaptionsTracklistRenderer?.captionTracks || []).length
   ```
   - If this is `0`, the video genuinely has no published captions → note it as **"transcript unavailable (no captions published)"** and move on.
   - If it is `≥ 1`, a transcript **exists**. Any empty result in the steps below is an **extraction failure to retry**, NOT "unavailable" — never silently drop it.

   **b. Expand the description** so the transcript button renders: click `#description #expand` (a.k.a. `#expand.ytd-text-inline-expander`). Wait ~1 s.

   **c. Click the *visible* "Show transcript" button with a REAL pointer click — verify, don't spam.** (Chrome `find` + `computer` left_click, not JS `.click()`.) There are usually **two** matching elements — one is a zero-width hidden duplicate that does nothing. Two failure modes seen in practice: the click **misses** (the button still says "Show transcript"), and a **blind second click toggles the panel closed**. So every click must be verified, never blind:
      1. `scrollIntoView({block:'center'})` the non-zero-width button, then **screenshot** and click its on-screen center by coordinate (the DOM `getBoundingClientRect` y is ~3–4% larger than the screenshot y — multiply by ~0.96, or just click the button as seen in the screenshot).
      2. **Verify the click registered:** re-read the button — its accessible label/text should have flipped to **"Hide transcript"**. If it still says "Show transcript," the click **missed** — re-screenshot (layout may have shifted) and click again. Do NOT click a button that already says "Hide transcript" (that closes it).
      3. Only after the label reads "Hide transcript" do you move to the poll (step d).
   Gate on the label, not on a fixed number of clicks — this avoids both the miss and the accidental toggle-closed.

   **d. Poll up to ~12 s** for a transcript panel to populate (do NOT use a flat 2 s wait — long podcasts need longer, and the panel lazy-loads). Segment rows come in two shapes:
   - **Classic** rows `ytd-transcript-segment-renderer`; text is in `.segment-text` (or the row's `yt-formatted-string`).
   - **Modern** rows `transcript-segment-view-model`; text is in `span.ytAttributedStringHost`.

   ⛔ **Do NOT select the panel by its `target-id`.** Panels have been seen with `target-id` of
   `engagement-panel-searchable-transcript`, `PAmodern_transcript_view`, **and `null`** — the null
   case is real (hit on the Fisherman's Landing video 2026-07-31) and a `target-id` filter silently
   excludes it, returning an empty string while the transcript is fully rendered on the page. That
   produced four bogus "extraction failed" retries in one run. **Select panels by whether they
   actually contain segment rows**, which is variant-agnostic and future-proof.

   Concatenate the per-segment **text** (do not scrape the panel's raw `.innerText` — the modern panel interleaves word-form timestamps like "25 seconds" / "17 minutes, 51 seconds" that pollute it). Reader snippet:
   ```js
   function readTranscript(){
     const SEG='ytd-transcript-segment-renderer, transcript-segment-view-model';
     // Select on CONTENT, never on target-id (which is sometimes null).
     const panels=[...document.querySelectorAll('ytd-engagement-panel-section-list-renderer')]
       .filter(p=>p.querySelector(SEG));
     // Last resort: rows rendered outside any recognised panel wrapper.
     const scopes=panels.length?panels:(document.querySelector(SEG)?[document]:[]);
     let best='';
     for(const p of scopes){
       const classic=[...p.querySelectorAll('ytd-transcript-segment-renderer')]
         .map(s=>(s.querySelector('.segment-text')||s).textContent.trim());
       const modern=[...p.querySelectorAll('transcript-segment-view-model')]
         .map(s=>(s.querySelector('span.ytAttributedStringHost')||{}).textContent?.trim()||'');
       const txt=[...classic,...modern].filter(Boolean).join(' ').replace(/\s+/g,' ').trim();
       if(txt.length>best.length) best=txt;
     }
     return best;
   }
   ```
   Consider the panel "ready" when the segment count stops increasing across two consecutive polls.

   **Before declaring an extraction failure, sanity-check with `document.querySelectorAll('ytd-transcript-segment-renderer, transcript-segment-view-model').length`.** If that count is > 0 but `readTranscript()` returned empty, the bug is in your selector, not in YouTube — do not burn retries or report a failure.

   **e. Retry loop on empty (up to ~4 attempts, not just once).** If captions existed (step a) but the poll returned empty, the transcript fetch didn't fire — some videos need several tries, and occasionally the classic panel opens as a permanent empty shell. Loop:
      1. **Close and re-open:** if the button reads "Hide transcript" but no segments rendered after ~12 s (empty shell), click once to close it, wait ~1 s, then re-click to reopen (verify the "Hide transcript" label each time as in step c) and poll again.
      2. If the button still reads "Show transcript" (the click kept missing), re-screenshot and re-click — the button drifts as the page settles, so re-measure its position every attempt rather than reusing old coordinates.
      3. Between attempts, a full page **reload** (then re-expand the description) clears a stuck toggle state and often succeeds where re-clicking didn't.
      4. Give it ~4 attempts total. Only if it STILL fails, record **"transcript extraction failed (captions exist) — retry next run"** in the Sources list and the Slack summary — this flags a real bug rather than masquerading as "no transcript." A single video failing this way is NOT an alert; note it and continue with the other channels.

   **f. Retrieve the text with `get_page_text` on the video page — not by chunking a JS return value.**
   Once the panel is open and populated, `get_page_text` returns the whole rendered transcript
   (plus title, description and view count) in **one** call. The `javascript_tool` return value is
   truncated at roughly 1,000 characters, so pulling a 12,000–25,000-char transcript through it costs
   ~20+ round trips per video and risks silent mid-transcript truncation. Use `readTranscript()` only
   as the readiness probe in step d (compare `.length` across polls), then call `get_page_text` once
   for the content. Note `get_page_text` output does include the modern panel's word-form timestamps
   ("25 seconds") interleaved with the text — that is cosmetic and does not impede analysis.
5. Analyze the transcript for the intel categories below.

### Intel to Extract from YouTube Transcripts

**1. 🐟 What's Biting**
Organize by species:
- Yellowtail (note size, location, biting conditions)
- Yellowfin Tuna
- Bluefin Tuna
- Wahoo
- Dorado / Mahi-Mahi
- Rockfish
- Other Species (calico bass, halibut, bonito, lingcod, barracuda, white seabass, etc.)

For each species: quantities caught if mentioned, size/weight, and whether biting was hot/slow/scattered.

**2. 🎣 Lures & Techniques**
- Surface iron / poppers (name, color, size if mentioned)
- Jigs (type, color, size)
- Live bait (sardines, mackerel, squid, etc.)
- Trolling details
- Fly-lining, dropper loops, yo-yo iron, etc.
- Rod/reel/line setups

**3. 📍 Where They're Biting**
Organize by:
- Offshore Banks (e.g., Farmorth Bank, 43 Fathom Bank, 9 Mile Bank, 371, etc.)
- Islands (Alijos Rocks, San Clemente, Catalina, San Nicolas, Coronados, etc.)
- Inshore / Coastal (La Jolla, Dana Point, Ensenada, kelp beds, beach, etc.)
- Long Range Mexico (note distance from San Diego if mentioned)

Note water temp, color, or conditions if mentioned.

---

## PART 2 — San Diego Landing Fish Count Websites

Visit each of the following landing pages and extract the last 7 days of daily fish count data.

### Landing Pages (all follow same process)

1. **Fisherman's Landing** — https://www.sandiegofishreports.com/landings/fishermans_landing.php
2. **H&M Landing** — https://www.sandiegofishreports.com/landings/h&m_landing.php
3. **Point Loma Sportfishing** — https://www.sandiegofishreports.com/landings/point_loma_sportfishing.php
4. **Seaforth Sportfishing** — https://www.sandiegofishreports.com/landings/seaforth_sportfishing.php

### Steps for Each SD Landing Page

1. Navigate to the main landing page URL.
2. Scroll to the bottom to find the **Archive** section (shows years 2025, 2026 with clickable month links: Jan, Feb, Mar, Apr, etc.).
3. Click the link for the **current month** in the current year (e.g., "Apr" under 2026). This loads the archive URL (format: `[base_url]?landing_id=XX&month=M&year=YYYY#historicals`). Landing IDs: Fisherman's = 22, H&M = 21, Point Loma = 23, Seaforth = 20. You can also fetch the archive HTML same-origin and parse the "Fish Counts for [Month] [Year]" table + "Annual Landing Totals" table directly.
4. On the archive page, scroll up to find the **"Historical Data"** section with a table titled **"Fish Counts for [Month] [Year]"**. Columns: Date, Boats, Anglers, Fish Count.
5. Extract only the rows covering the **last 7 days** from today's date.
6. Also capture the **Annual Landing Totals** table (key species: Bluefin Tuna, Yellowfin Tuna, Yellowtail, Calico Bass, Halibut, Rockfish — 2026 YTD vs. 2025 YTD).

**Per landing, summarize:**
- Each day in the last 7 days: date, boats/trips, anglers, species caught with counts
- Which species dominated this week
- Any standout catches (tuna, unusual pelagics, big yellowtail counts)

---

## PART 3 — Long Range Boat Reports (LongRangeSportfishing.net)

**URL:** https://www.longrangesportfishing.net/fishreports.php

This site has **no archive or calendar** — it uses simple pagination. The page shows a table with columns: Date, Report (title + brief snippet + "more »" link), Author (reporter name + boat name), Audio.

### Steps

1. Navigate to https://www.longrangesportfishing.net/fishreports.php
2. The most recent reports appear at the top of the table on Page 1. Extract all report rows from the **last 7 days** using get_page_text or JavaScript (look for the table rows, get Date, title, snippet, and boat name from each row).
3. If the 7-day window is not fully covered by page 1, look for a "Next>" link at the bottom of the table (format: "Page 1 of XXXX Next>") and navigate to page 2 to get the remaining days.
4. For any report with a particularly noteworthy title (e.g., "Limits of Bluefin", "Wahoo!", "Wide Open"), click the "more »" link to read the full report text for additional detail on species, quantities, and locations.
5. Organize the extracted reports **by boat name**, listing each boat's reports for the week with dates and key catches.

**What to extract per report:**
- Boat name
- Date
- Report title
- Key species caught (from snippet or full report)
- Location or fishing area if mentioned
- Notable catches (limits, big fish, unusual species)

**Note:** Long range reports cover multi-day trips to Mexican waters (Cedros Island, Alijos Rocks, Baja coast, offshore banks). These results feed into the overall long range section of the report, not the inshore landing counts.

---

## PART 4 — Weekly Conditions (Wind / Swell / SST / Moon + PDF Map Briefing)

This section is **fully automated and does NOT use Chrome.** It runs a self-contained Python script
that pulls live data, renders the temperature-break and water-color maps, and compiles them into a
single dated PDF briefing. (We render headlessly rather than screenshotting Catalysst because browser
screenshots cannot be saved to disk on the scheduled run.)

⛔ **CRITICAL — never hand-write the Conditions data.** The moon line and every wind / swell / SST
value MUST come from the stdout of `conditions.py`, pasted verbatim. Do NOT estimate, improvise,
reformat, or "fill in" these numbers yourself, and do NOT add interpretive claims (e.g. "favorable
for pelagics", "strong tidal action"). If `conditions.py` cannot be found or run, write exactly:
**"🌊 Conditions — unavailable this run ([one-line reason])"** and move on. A missing or failed script
is NEVER a reason to generate the section by hand. (A past run that used mph, single-snapshot values,
and editorial notes was an INCORRECT improvisation — do not repeat it.)

**Locating the script:** it lives in this project folder (Weekly Saltwater Fishing Report). If
`python3 "conditions.py"` fails with "file not found," search the mounted workspace first:
`find /sessions -name conditions.py 2>/dev/null`, then run it from that directory.

### Steps

1. Install dependencies (first run in a fresh environment):
   `pip install matplotlib numpy ephem reportlab pillow --break-system-packages -q`
2. Run the generator from the project folder:
   `python3 "conditions.py"`
   (sandbox path: `/sessions/<session>/mnt/Weekly Saltwater Fishing Report/conditions.py`)
3. The script prints the ready-to-paste **Conditions** Markdown to stdout, renders the four maps,
   and compiles them into a single dated **PDF briefing** at
   `conditions_briefings/conditions_YYYYMMDD.pdf`. At the very end it prints that PDF's macOS path
   inside a `<!-- BRIEFING ... -->` comment — capture it for the Day One text and the Slack reminder.

ℹ️ **Maps are embedded as images (PART 5); the PDF is a bundled fallback.** The Day One *CLI's*
attachment import is broken in this build — it records a moment but never embeds the bytes, so
anything attached via `create_entry_with_attachments` shows as a blank placeholder. The job therefore
embeds the four map PNGs by **pasting image data into the open entry** (PART 5), which creates real,
syncing photo moments. The script still also builds the self-contained PDF (maps + numbers + moon) as
a portable artifact and a manual-drag fallback for runs where the GUI paste can't execute; the Slack
post carries its path either way.

### What it produces
- A **Moon** line for the week (phase, % illumination, short bite note).
- **Core regions — always include:** Southern California Bight, Northern Baja, San Clemente & Catalina.
- **Offshore banks — modeled:** Tanner/Cortez, Cedros/Guadalupe, Magdalena Bay, The Ridge, Alijos
  Rocks. The script outputs ALL of them, but **include a bank's line in the report ONLY if this
  week's YouTube or long-range reports actually mention that area** — otherwise delete that line.
- **One PDF briefing** (`conditions_briefings/conditions_YYYYMMDD.pdf`) with the region tables plus
  four maps — temp-break (NOAA MUR SST) and water-color (chlorophyll) for SoCal + Baja. Loose map PNGs
  live in `conditions_maps/`. Both folders auto-prune files older than ~8 weeks.

### Data sources (no login, no Chrome)
- Wind / swell / SST numbers — Open-Meteo Marine + Weather APIs (wind in KNOTS).
- Temperature-break maps — NOAA MUR 1 km SST via NOAA CoastWatch ERDDAP.
- Water-color maps — DINEOF gap-filled chlorophyll via NOAA CoastWatch ERDDAP. Gap-filled = clean
  coverage even under clouds. `conditions.py` tries `CHL_DATASETS` in order and prints the dataset
  and its lag under each map: near-real-time 9 km first (~2-day lag), then the science-quality 9 km
  products (~11-day lag) as backstops. The old 2 km dataset `noaacwNPPN20S3ASCIDINEOF2kmDaily` was
  **retired by NOAA and now 404s** — that outage is what dropped both water-color maps on 2026-07-31.
- Moon — `ephem`.

### Graceful degrade
- If a map source (NOAA MUR or chlorophyll) does not respond, the script still prints the text and
  notes that map type "unavailable"; if the PDF can't be built it says so. Post the report with
  whatever came back. This is NOT an alert condition.
- Open-Meteo numbers are the backbone; if a single region fails it is marked "unavailable" inline.
- Catalysst (app.catalysst.net) remains Ed's richer interactive tool but is NOT part of this run.

---

## Report Format

Compile all data into a single Day One journal entry:

---
# 🎣 Weekly Saltwater Fishing Report — [Date]

## Sources This Week

**YouTube Channels:**
[List each channel: video title reviewed, or "No new video this week", or the genuine-vs-failed transcript status]

**SD Landing Fish Count Sites:**
Fisherman's Landing, H&M Landing, Point Loma Sportfishing, Seaforth Sportfishing

**Long Range:**
LongRangeSportfishing.net

---

## 🌊 Conditions — Week of [Date Range]

[Paste the Markdown printed by `conditions.py` (PART 4) VERBATIM — the moon line, the region lines
(wind in kt, week ranges, the core/banks split), AND the "📄 Visual briefing" line with the PDF path.
Do NOT rewrite, reformat, or invent these numbers. The only editing allowed: delete the Offshore-bank
lines for areas this week's reports did NOT mention. Do NOT attach the maps or PDF via the Day One
connector (its attachment function is broken — see PART 4); the PDF path is included as text so Ed can
drop it in manually. If the script could not run, replace this whole section with a single line:
"🌊 Conditions — unavailable this run." This is a forward-looking briefing header.]

---

## 🐟 What's Biting (YouTube Intel)

[By species, combining all channel transcripts. Note which channel reported each item.]

---

## 🎣 Lures & Techniques

[All tackle and methods mentioned across channels, noting which species each was used for.]

---

## 📍 Where They're Biting (YouTube Intel)

[Organized by: Offshore Banks / Islands / Inshore / Long Range Mexico]

---

## 🏚️ SD Landing Fish Counts — Last 7 Days

### Fisherman's Landing
[Daily fish counts for last 7 days — date, boats, anglers, species+counts]
[Standouts and weekly summary]

### H&M Landing
[Daily fish counts for last 7 days]
[Standouts and weekly summary]

### Point Loma Sportfishing
[Daily fish counts for last 7 days]
[Standouts and weekly summary]

### Seaforth Sportfishing
[Daily fish counts for last 7 days]
[Standouts and weekly summary]

**Combined SD Landing Highlights:**
[2–3 sentences: what's coming in most at the docks, any tuna or pelagics showing, how 2026 YTD compares to 2025]

---

## 🚢 Long Range Boat Reports — Last 7 Days

[Organized by boat name. For each boat: dates active, locations fished, species caught, notable catches.]

Example format:
**Polaris Supreme** (4/15–4/17): Bluefin tuna limits reported; 77 lb BFT on popper...
**Independence** (4/14–4/17): Yellowtail on surface near Baja coast; also BFT limits...
**American Angler** (4/13–4/16): Wahoo + dorado + yellowtail mixed bag; found bluefin on way home...
**Royal Star** (4/14–4/16): Working coastal for yellowtail; also some BFT...

[Include all boats that had reports this week]

---

## 📝 Key Takeaways

[3–5 bullet points: the most important intel from the entire report — YouTube + landings + long range combined. "If you only read one section" summary.]

---

Save the completed report as a new Day One journal entry using **`mcp__dayone__create_journal_entry`** (text only), in the journal named "Saltwater Fishing Journal", tagged with: fishing, saltwater, weekly-report, SoCal, Baja. **Capture the entry UUID the tool returns — the next step (PART 5) needs it.**

**Do NOT use `create_entry_with_attachments`.** The Day One CLI's media import is broken in this build — it records a moment but never embeds the bytes, so attached images become blank placeholders. Embed the maps with the clipboard-paste method in PART 5 instead (verified to create real, syncing photo moments that render on desktop + mobile).

---

## PART 5 — Insert the Conditions maps into the entry (image embed — the working method)

After the text entry is saved and you have its UUID, embed this run's `conditions_maps/*.png` images
inline — up to four, in this order: SoCal temp-break, SoCal water-color, Baja temp-break, Baja
water-color. **Skip this step entirely** if the Conditions section was "unavailable this run" (no maps
were produced). Fewer than four is normal when a map source failed; embed what exists.

Why this works when the connector doesn't: the Day One CLI cannot embed media in this build, but
**pasting image data into an open entry creates a proper, syncing photo moment** (the file lands in
`DayOnePhotos/<md5>.png` with a `![](dayone-moment://…)` marker — identical to the GUI "+" button).
The helper script performs the whole sequence, including the keystroke.

⚠️ **Reliability rules:**
(a) A freshly-saved entry opens in *read* mode — the first map must go through `paste`, which opens
the entry via `dayone://edit?entryId=…` so the editor has focus; sending a paste at a read-mode entry
goes nowhere. (b) Use `clip_paste` for maps 2..N — it deliberately does **not** re-open the entry,
because re-opening drops back to read mode. Do not interleave any other keystrokes between pastes.
(c) Every `paste`/`clip_paste` prints `PASTED=<count>`; that count must rise by one each time. If one
doesn't move, re-run that single `clip_paste` once.

Helper: `tools/dayone_attach.sh` in the project folder (`FISHING_PROJECT_DIR` env var overrides the
default path).

**Get this run's map list first:** `bash tools/dayone_attach.sh list`. It prints only maps stamped
with **today's** date, in insert order, and prints `MISSING:<file>` to **stderr** for any map that
was not produced this run. Embed exactly what stdout lists — never substitute an older render, and
expect fewer than 4 whenever a map source failed (see PART 4 graceful degrade).

### Use the automated Bash path — do NOT use computer-use

⛔ **`request_access` for Day One CANNOT be approved during a scheduled run.** It returns
"Computer-use access to 'Day One' … can't be approved during a scheduled run", and the error states
retrying returns the same result. Any earlier instruction here claiming that a one-time **Run Now**
makes Cowork store the approval for later runs was **wrong** — it does not, and the session allowlist
comes back empty. Do not spend a call on `request_access`; there is no GUI-permission path on a
scheduled run.

You do not need one. The helper's `paste` / `clip_paste` subcommands issue the Cmd+V **themselves**
via `osascript` + System Events, so the whole step runs from **Bash**:

```bash
cd "/Users/edmatibag/Documents/Claude/Projects/Weekly Saltwater Fishing Report"
UUID="<entry uuid from the Day One save>"
mapfile -t MAPS < <(bash tools/dayone_attach.sh list)   # today's maps only
bash tools/dayone_attach.sh paste      "$UUID" "${MAPS[0]}"   # opens + focuses the entry, then pastes
for m in "${MAPS[@]:1}"; do
  bash tools/dayone_attach.sh clip_paste "$UUID" "$m"         # keeps edit focus, no re-open
done
bash tools/dayone_attach.sh count "$UUID"                     # must equal ${#MAPS[@]}
```

Each `paste` / `clip_paste` prints `PASTED=<new_count>`. That count must increase by one per map; if
one doesn't move, re-run that single `clip_paste` once before giving up.

**Prerequisite:** System Events keystrokes require the host app to hold macOS **Accessibility**
permission (System Settings → Privacy & Security → Accessibility). Without it the keystroke is
blocked and `PASTED=` will not advance — that is the one failure mode to expect, and it is a
one-time manual grant Ed must make; it cannot be granted from inside a run.

**Fallback:** if the counts never advance, **do NOT fail the task** — the text report and the
Conditions PDF are already saved. Post the report and let the Slack ACTION block (below) remind Ed to
drop the PDF in manually. Embedded maps are the goal; the PDF reminder is the fallback.

*(The legacy `stage` / `clip` subcommands still exist and only load the clipboard, leaving the Cmd+V
to a GUI caller. They are unusable on a scheduled run for the reason above — prefer `paste` /
`clip_paste`.)*

---

## ✅ Success Notification — Slack (after a successful run)

**Run this immediately AFTER the Day One entry has been saved successfully.** This is the normal "report posted" confirmation — it fires on every successful run, not on errors.

Post a message to Slack using `mcp__0d87112c-54fd-4221-ad16-0fac875e1609__slack_send_message`:
- **channel_id:** `<SLACK_CHANNEL_ID>`  (workspace: <SLACK_WORKSPACE> — channel #fishing-report-alerts)
- **message:** A concise success summary, for example:

```
:fish: *Weekly Saltwater Fishing Report — [Date] posted to Day One.*
• Sources: YouTube [N of 6 channels with new videos] | SD Landings [4 of 4] | Long Range [N boats]
• Skipped / unavailable: [list any channels with no new video, "transcript unavailable (no captions)", or "transcript extraction failed — retry next run", or "none"]
• Maps: [N of 4 Conditions maps embedded in the entry]
• Top takeaway: [one-line headline from the Key Takeaways section]
— Cowork Automated Alert
```

If **all four maps embedded** (PART 5 succeeded), that's the whole message — no action needed from Ed.

**Only if one or more maps did NOT embed** (PART 5 fell back), append this ACTION block so Ed can drop
the PDF in manually:

```
:round_pushpin: *ACTION — maps didn't auto-embed this run; add the Conditions PDF to today's entry:*
Open the file below and drag it into the entry with Day One's "+" button.
`[full PDF path from the conditions.py <!-- BRIEFING --> footer, e.g. /Users/edmatibag/Documents/Claude/Projects/Weekly Saltwater Fishing Report/conditions_briefings/conditions_YYYYMMDD.pdf]`
(On Mac: Finder → Cmd+Shift+G → paste the path.)
```

Fill the bracketed fields from the actual run; paste the real PDF path from the script's
`<!-- BRIEFING -->` footer into the code span (Slack shows it as copyable text — local file paths are
not clickable links, so leave it as a plain path, not a `<file://…>` link). If the Conditions section
was unavailable this run (no maps), drop both the Maps line and the ACTION block. If the Slack post
fails, do not treat it as a task failure — the report is already saved; note the Slack failure and continue.

---

## 🚨 Alert Protocol — Notify Ed When Blocked or an Error Occurs

**Trigger this alert and stop the task immediately when:**

**Category 1 — System / MCP Error:**
- An MCP service or tool is unavailable or returns persistent errors
- A required connector or permission is missing
- Task is stalled or taking excessively long

**Category 2 — User Action Required:**
- Chrome browser is not open or cannot be accessed
- Login or authorization is needed
- Any step requires Ed's direct interaction

Note: a failure of the Conditions step (PART 4) is NOT an alert condition — write "🌊 Conditions — unavailable this run" and post the rest of the report. A single YouTube video's transcript failing to extract is also NOT an alert — note it in Sources ("transcript extraction failed — retry next run") and continue. Only the Chrome-dependent scraping steps (Parts 1–3) failing wholesale, or the Day One save, trigger alerts.

**How to send the alert — fire Gmail and Slack in parallel (both), then Apple Notes only as a fallback:**

**Step 1 — Gmail (primary):**
1. Navigate to https://mail.google.com/mail/u/0/#compose
2. Fill compose form via JavaScript:
   - To: <ALERT_EMAIL>
   - Subject: ⚠️ Weekly Saltwater Fishing Report — [Category]: [One-line issue]
   - Body: Scheduled Task: weekly-saltwater-fishing-report | Date/Time: [now] | Alert Category: [category] | Issue: [2–3 sentences] | Steps completed: [brief summary] | Action needed: [specific thing Ed must do] | — Cowork Automated Alert
3. Send via Cmd+Enter or click Send button.

**Step 2 — Slack (sent at the same time as Gmail):**
Post to Slack using `mcp__0d87112c-54fd-4221-ad16-0fac875e1609__slack_send_message`:
- **channel_id:** `<SLACK_CHANNEL_ID>`  (#fishing-report-alerts, workspace <SLACK_WORKSPACE>)
- **message:**

```
:warning: *Weekly Saltwater Fishing Report — [Category] alert*
• Issue: [2–3 sentences]
• Steps completed: [brief summary]
• Action needed: [specific thing Ed must do]
• Time: [now]
— Cowork Automated Alert
```

Note: the Gmail alert goes through the Chrome compose page, so if Chrome itself is the failure, Gmail may not send — the Slack alert uses the MCP (independent of Chrome) and will usually still get through. Send both regardless.

**Step 3 — Apple Notes (fallback only, if BOTH Gmail and Slack fail):**
Use mcp__Read_and_Write_Apple_Notes__add_note:
- Title: ⚠️ TASK ALERT: Weekly Saltwater Fishing Report — [Date]
- Body: Same content as the alert above

**After alert:** Stop the task. Do not retry indefinitely.

---

ATTENTION-LAYER FOOTER (per ESCALATION-POLICY.md, added 2026-07-28 with Ed's approval):

1. Noteworthy but NON-BLOCKING findings from this run (skipped/malformed inputs, auth warnings, source-format drift, anything Ed should eventually see but that shouldn't interrupt him) -> append one Lane-2 JSON line to /Users/edmatibag/Documents/Claude/Projects/AI-orchestration-layer/runs/digest.jsonl:
   {"ts": "<ISO-8601 local>", "severity": "info|minor", "category": "<short-kebab>", "text": "<standalone description>", "source": "weekly-saltwater-fishing-report", "status": "new"}
   Append-only: never edit, re-deliver, or delete existing rows -- the evening-digest task owns delivery and status transitions. Do not file duplicates of an item already in the queue.

2. If you CANNOT complete this job, say so explicitly in your final report AND file a Lane-2 row describing what failed (severity "minor"; use "major" only if data was lost).

3. ALWAYS end the run -- success or failure -- by appending one heartbeat line to /Users/edmatibag/Documents/Claude/Projects/Mission-Control-Dashboard/runs/heartbeat.jsonl:
   {"task": "weekly-saltwater-fishing-report", "ts": "<ISO-8601 local>", "status": "ok|partial|failed", "note": "<one line>"}
   The ops-watcher reads this to distinguish a run that completed from one that started and died.
