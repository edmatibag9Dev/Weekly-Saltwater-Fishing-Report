# Weekly schedule — setup (Cowork scheduled task)

The report runs every **Friday at 9:02 AM (America/Los_Angeles)** as a **Cowork scheduled task**
(not macOS launchd) — because it drives the Claude-in-Chrome extension and Cowork's connectors
(Day One, Slack, Gmail), which only exist inside the Cowork app.

- **Task ID:** `weekly-saltwater-fishing-report`
- **Cron:** `0 9 * * 5` (local time; Cowork adds a few minutes of dispatch jitter → ~9:02)
- **Live prompt:** `~/.claude/scheduled-tasks/weekly-saltwater-fishing-report/SKILL.md`
- **Reference copy:** this repo's `SKILL.md` — keep the two in sync.

Scheduled tasks run while the Cowork app is open; if it's closed when the task is due, it runs on
next launch.

## Runtime prerequisites (Fridays)

- **Google Chrome open + signed in** with the Claude-in-Chrome extension (Parts 2–3 scraping, plus
  the Part 1 YouTube fallback; the primary YouTube path `tools/yt_transcript.py` is headless).
- **Day One app running** (entry save).
- **Slack / Gmail / Apple Notes** connectors available (success post + error alerts).
- Sandbox network reaches `open-meteo.com` and `coastwatch.pfeg.noaa.gov` / `coastwatch.noaa.gov`
  (Conditions — no Chrome needed).

## Edit the task

1. Open this project in Cowork.
2. Update this repo's `SKILL.md`, then re-sync the live task — either via the `/schedule` skill
   (reference this `SKILL.md`) or by editing `~/.claude/scheduled-tasks/weekly-saltwater-fishing-report/SKILL.md`.
3. After any change, **Run Now** once to confirm and to pre-approve any tool permissions (Cowork
   stores per-task approvals so future runs don't pause).

## Notifications

- **Success (every run):** Slack `#fishing-report-alerts` summary + the Conditions PDF path reminder.
- **Error:** Gmail + Slack in parallel; Apple Notes only if both fail. A Conditions-step failure is
  **not** an alert — the report posts with `🌊 Conditions — unavailable this run`.
