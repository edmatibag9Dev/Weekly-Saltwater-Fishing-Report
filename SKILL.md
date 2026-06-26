---
name: weekly-saltwater-fishing-report
description: Weekly saltwater fishing report — SoCal/Baja YouTube transcripts + 4 SD landing fish counts + long range boat reports → Day One journal entry
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
4. Extract the full transcript using the Chrome extension:
   - Find and click the "Show transcript" button using JavaScript: find all buttons/role="button" elements, find the one with text "Show transcript", click it
   - Wait 2 seconds for the transcript panel to load
   - Extract text from the panel: find ytd-engagement-panel-section-list-renderer whose target-id includes "transcript", use .innerText, strip timestamp lines (patterns like "X:XX" and "X minutes, Y seconds")
   - Store in window._transcript; retrieve in 4,000-char chunks as needed (transcripts can be 15,000–25,000 chars)
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
3. Click the link for the **current month** in the current year (e.g., "Apr" under 2026). This loads the archive URL (format: `[base_url]?landing_id=XX&month=M&year=YYYY#historicals`).
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

## PART 4 — Weekly Conditions (Wind / Swell / SST / Moon + Temp-Break Maps)

This section is **fully automated and does NOT use Chrome.** It runs a self-contained Python script
that pulls live data, renders the temperature-break and water-color maps, and compiles them into a
single dated PDF briefing. (We render headlessly rather than screenshotting Catalysst because browser
screenshots cannot be saved to disk on the scheduled run.)

> ⛔ **CRITICAL — never hand-write the Conditions data.** The moon line and every wind / swell /
> SST value MUST come from the stdout of `conditions.py`, pasted verbatim. Do NOT estimate,
> improvise, reformat, or "fill in" these numbers yourself, and do NOT add interpretive claims
> (e.g. "favorable for pelagics"). If `conditions.py` cannot be found or run (file missing, deps
> fail, network down), write exactly: **"🌊 Conditions — unavailable this run ([one-line reason])"**
> and move on. A missing/failed script is NEVER a reason to generate the section by hand.
>
> **Locating the script:** it lives in this project folder. If `python3 "conditions.py"` from the
> project folder fails with "file not found," search the mounted workspace for `conditions.py`
> (e.g. `find /sessions -name conditions.py 2>/dev/null`) and run it from there before giving up.

### Steps

1. Install dependencies (first run in a fresh environment):
   ```
   pip install matplotlib numpy ephem --break-system-packages -q
   ```
2. Run the generator from the project folder:
   ```
   python3 "conditions.py"
   ```
   (sandbox path: `/sessions/<session>/mnt/Weekly Saltwater Fishing Report/conditions.py`)
3. The script prints the ready-to-paste **Conditions** Markdown to stdout, renders the four maps,
   and compiles them into a single dated **PDF briefing** at
   `conditions_briefings/conditions_YYYYMMDD.pdf`. At the very end it prints that PDF's macOS path
   inside a `<!-- BRIEFING ... -->` comment — capture it for the Day One text and the Slack reminder.

> ℹ️ **Why a PDF (not Day One image attachments):** the Day One connector's attachment function is
> broken in this setup — it records the count but never embeds the image data, so attached PNG/JPG
> show as blank placeholders. The job therefore does NOT attach anything via the connector. It saves
> a self-contained PDF (maps + numbers + moon) that Ed manually drops into the journal entry using
> Day One's "+" add-media button (verified to render on desktop and mobile). The Slack success post
> reminds Ed with the PDF's path.

### What it produces
- A **Moon** line for the week (phase, % illumination, and a short bite note).
- **Core regions — always include:** Southern California Bight, Northern Baja, San Clemente & Catalina.
- **Offshore banks — modeled:** Tanner/Cortez, Cedros/Guadalupe, Magdalena Bay, The Ridge, Alijos
  Rocks. The script outputs ALL of them, but **include a bank's line in the report ONLY if this
  week's YouTube or long-range reports actually mention that area** — otherwise delete that line.
- **One PDF briefing** (`conditions_briefings/conditions_YYYYMMDD.pdf`) containing the region tables
  plus four maps — temp-break (NOAA MUR SST) and water-color (chlorophyll) for SoCal + Baja. The
  loose map PNGs live in `conditions_maps/`. Both folders auto-prune files older than ~8 weeks.

### Data sources (no login, no Chrome)
- Wind / swell / SST numbers — Open-Meteo Marine + Weather APIs.
- Temperature-break maps — NOAA MUR 1 km SST via NOAA CoastWatch ERDDAP.
- Water-color maps — VIIRS (SNPP+NOAA-20) + Sentinel-3A OLCI **DINEOF gap-filled** chlorophyll
  (`noaacwNPPN20S3ASCIDINEOF2kmDaily`) via NOAA CoastWatch ERDDAP. Gap-filled = clean coverage
  even under clouds; science-quality lag is ~10 days (chlorophyll is a slow-moving signal — fine).
- Moon — `ephem`.

### Region points (edit `REGIONS` in conditions.py to tune)
SoCal Bight 32.9/-117.8 · N. Baja 31.6/-116.9 · San Clemente–Catalina 33.1/-118.5 ·
Tanner-Cortez 32.5/-119.2 · Cedros/Guadalupe 28.2/-115.2 · Mag Bay 24.4/-112.2 ·
The Ridge 25.3/-114.6 · Alijos Rocks 24.95/-115.73.

### Graceful degrade
- If NOAA MUR does not respond, the script still prints the text and notes "Temp-break maps
  unavailable this week" — post the report without maps. This is NOT an alert condition.
- Open-Meteo numbers are the backbone; if a single region fails it is marked "unavailable" inline
  and the rest proceed.
- Catalysst (app.catalysst.net, International/All-Access tier) remains Ed's richer **interactive**
  tool — bathymetry, chlorophyll, AIS, contour styling — but it is NOT part of the automated run.

---

## Report Format

Compile all data into a single Day One journal entry:

---
# 🎣 Weekly Saltwater Fishing Report — [Date]

## Sources This Week

**YouTube Channels:**
[List each channel: video title reviewed, or "No new video this week"]

**SD Landing Fish Count Sites:**
Fisherman's Landing, H&M Landing, Point Loma Sportfishing, Seaforth Sportfishing

**Long Range:**
LongRangeSportfishing.net

---

## 🌊 Conditions — Week of [Date Range]

[Paste the Markdown printed by `conditions.py` (PART 4) VERBATIM — the moon line, the region
lines (wind in kt, week ranges, the core/banks split), AND the "📄 Visual briefing" line with the
PDF path. Do NOT rewrite, reformat, or invent these numbers. The only editing allowed: delete the
Offshore-bank lines for areas this week's reports did NOT mention. Do NOT attach the maps or PDF via
the Day One connector (its attachment function is broken — see PART 4); the PDF path is included as
text so Ed can drop it in manually. If the script could not run, replace this whole section with a
single line: "🌊 Conditions — unavailable this run." This is a forward-looking briefing header; it frames the
retrospective catch intel that follows.]

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

Save the completed report as a new Day One journal entry using **`mcp__dayone__create_journal_entry`** (text only), in the journal named "Saltwater Fishing Journal", tagged with: fishing, saltwater, weekly-report, SoCal, Baja.

**Do NOT use `create_entry_with_attachments`.** The Day One connector's attachment function is broken in this setup — attached images/PDFs become blank placeholders. The Conditions section already contains the PDF's path as text; Ed adds the PDF to the entry himself with Day One's "+" add-media button. The Slack success post (below) repeats the PDF path as his reminder.

---

## ✅ Success Notification — Slack (after a successful run)

**Run this immediately AFTER the Day One entry has been saved successfully.** This is the normal "report posted" confirmation — it fires on every successful run, not on errors.

Post a message to Slack using `mcp__0d87112c-54fd-4221-ad16-0fac875e1609__slack_send_message`:
- **channel_id:** `<SLACK_CHANNEL_ID>`  (workspace: <SLACK_WORKSPACE> — channel #fishing-report-alerts)
- **message:** A concise success summary, for example:

```
:fish: *Weekly Saltwater Fishing Report — [Date] posted to Day One.*
• Sources: YouTube [N of 6 channels with new videos] | SD Landings [4 of 4] | Long Range [N boats]
• Skipped / unavailable: [list any channels with no new video or "transcript unavailable", or "none"]
• Top takeaway: [one-line headline from the Key Takeaways section]

:round_pushpin: *ACTION — add the Conditions PDF to today's journal entry:*
Open the file below and drag it into the entry with Day One's "+" button.
`[full PDF path from the conditions.py <!-- BRIEFING --> footer, e.g. /Users/edmatibag/Documents/Claude/Projects/Weekly Saltwater Fishing Report/conditions_briefings/conditions_YYYYMMDD.pdf]`
(On Mac: Finder → Cmd+Shift+G → paste the path.)
— Cowork Automated Alert
```

Fill the bracketed fields from the actual run; paste the real PDF path from the script's `<!-- BRIEFING -->` footer into the code span (Slack shows it as copyable text — local file paths are not clickable links, so leave it as a plain path, not a `<file://…>` link). If the Conditions PDF was unavailable this run, drop the ACTION block. If the Slack post fails, do not treat it as a task failure — the report is already saved; simply note the Slack failure and continue.

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
