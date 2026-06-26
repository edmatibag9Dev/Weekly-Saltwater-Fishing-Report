# Weekly Saltwater Fishing Report — Setup & Connector Guide

## Required Connectors

All of these must be connected in Cowork for the task to run successfully.

### 1. Claude in Chrome (Browser Extension)
**Purpose:** Scrapes YouTube video pages (transcripts), SD Fish Reports landing pages, and LongRangeSportfishing.net  
**How to verify:** Open Chrome → look for the Claude extension icon in the toolbar. It should show as connected.  
**Critical:** Chrome must be **open and not minimized** at 9:02 AM on Fridays. The browser doesn't need to be on any specific page.  
**Install:** Chrome Web Store → search "Claude for Chrome" → install → sign in with your Anthropic account.

### 2. Day One MCP
**Purpose:** Creates the final weekly report journal entry in Saltwater Fishing Journal  
**Journal used:** `Saltwater Fishing Journal`  
**How to verify:** In Cowork → Settings → Connectors → Day One should show "Connected"  
**Troubleshooting:** Day One app must be running on your Mac. If it's not open, the MCP can't write entries.

### 3. Gmail MCP
**Purpose:** Sends alert emails to <ALERT_EMAIL> if the task hits an error or needs your intervention  
**Alert email:** <ALERT_EMAIL>  
**How to verify:** In Cowork → Settings → Connectors → Gmail should show "Connected"  
**Note:** This is only used for error alerts — not for the actual report output.

### 4. Slack MCP
**Purpose:** Posts to **#fishing-report-alerts** (workspace: *<SLACK_WORKSPACE>*) on every run — a success confirmation when the report posts, and an error alert (in parallel with Gmail) when a run is blocked  
**Channel:** `#fishing-report-alerts` (ID `<SLACK_CHANNEL_ID>`, private)  
**How to verify:** In Cowork → Settings → Connectors → Slack should show "Connected"  
**Critical:** Because the channel is **private**, the Claude/Cowork Slack app must be a member of it. If posts stop working, re-invite the app to the channel.

### 5. Apple Notes MCP (Fallback)
**Purpose:** Last-resort alert if **both** Gmail and Slack fail when an error occurs  
**How to verify:** In Cowork → Settings → Connectors → Apple Notes should show "Connected"

---

## Schedule Details

| Setting | Value |
|---------|-------|
| Task ID | `weekly-saltwater-fishing-report` |
| Cron | `0 9 * * 5` (every Friday) |
| Run time | 9:02 AM Pacific (with ~2 min jitter) |
| Next run | Every Friday morning |
| Output | Day One — Saltwater Fishing Journal |

---

## What Needs to Be Running on Friday Mornings

- ✅ Your Mac must be **awake** (not sleeping) at 9 AM
- ✅ **Chrome** must be open (any page is fine)
- ✅ **Claude in Chrome extension** must be active (signed in)
- ✅ **Day One** app must be running
- ✅ **Slack** connector must be connected (for success + error notifications)
- ✅ **Cowork** must be running (it always runs in the background if installed)

---

## To Update the Task Instructions

1. Edit the `SKILL.md` in this project folder (your working copy)
2. Open a Cowork session in this project
3. Say: *"Update the weekly-saltwater-fishing-report scheduled task with the contents of SKILL.md"*
4. Claude will use the `/schedule` skill to push the update

Or navigate directly to `~/Claude/Scheduled/weekly-saltwater-fishing-report/SKILL.md` in Finder and edit it — changes take effect on the next run.

---

## To Add a New YouTube Channel

1. Open `SKILL.md` in this folder
2. Find the `## PART 1 — YouTube Channels to Check` section
3. Add the new channel URL to the numbered list
4. Save, then update the Scheduled task (steps above)

## To Add a New SD Landing

1. Open `SKILL.md` in this folder
2. Find `## PART 2 — San Diego Landing Fish Count Websites`
3. Add the new landing URL
4. Save, then update the Scheduled task

---

## Troubleshooting

**"Chrome is not connected" alert received:**
- Open Chrome on your Mac
- Click the Claude extension icon and make sure you're signed in
- Manually run the task: open Cowork → type `run weekly-saltwater-fishing-report`

**Report didn't save to Day One:**
- Make sure Day One app is open
- Check Day One → Saltwater Fishing Journal for any partial entry
- Manually re-run: open Cowork → type `run weekly saltwater fishing report`

**Transcript extraction failing for some channels:**
- This is expected for newer YouTube videos that use the modern transcript format
- Those channels are noted as "transcript unavailable" in the report
- No action needed — the task will still complete using available sources

**Task ran but no email alert received:**
- Check Gmail spam folder
- Verify Gmail MCP is still connected in Cowork settings
- Check **#fishing-report-alerts** in Slack — the error alert fires there in parallel with Gmail

**No Slack notification received (success or error):**
- Verify the Slack MCP is connected in Cowork settings
- Confirm the Claude/Cowork Slack app is still a member of **#fishing-report-alerts** (it's a private channel) — re-invite it if it was removed
- Channel ID is `<SLACK_CHANNEL_ID>`; if the channel was recreated, the ID changes and SKILL.md must be updated

---

## Manual Run

You can trigger the report at any time by opening Cowork in this project and saying:
> *"Run the weekly saltwater fishing report now"*

Or from any Cowork project:
> *"Run scheduled task weekly-saltwater-fishing-report"*
