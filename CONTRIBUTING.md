# Contributing Standards
# Ed Matibag — Global GitHub Commit & README Rules
# Canonical copy: ~/Documents/Claude/CONTRIBUTING.md

---

## Commit Message Format

Every commit must follow this structure — no exceptions.

```
<type>(<scope>): <subject line — max 72 chars, imperative mood>

<body — minimum 3 bullets describing what changed and why>

- What was built or changed
- Why it was needed or what problem it solves
- Any known limitations, workarounds, or follow-up items
```

### Types

| Type | Use when |
|------|----------|
| `feat` | New feature or new file added |
| `fix` | Bug fix or correction |
| `data` | Data update — new scrape, refresh, or content change |
| `docs` | README or documentation only change |
| `refactor` | Code restructure with no behavior change |
| `chore` | Config, tooling, or maintenance |

### Rules

- **`feat`, `fix`, `data` commits require a body with ≥ 3 bullets.** No one-liners.
- Subject line: imperative mood ("Add month filter" not "Added month filter")
- Body bullets must be specific — not generic filler like "updated code"
- If a feat or fix touches the README, say so in the body

### Examples

**Good:**
```
feat(conditions): add chlorophyll water-color maps to the weekly briefing

- Added VIIRS+OLCI DINEOF gap-filled chlorophyll source and a draw_chl()
  renderer so the PDF now carries SoCal + Baja water-color maps alongside SST
- Gap-filled product chosen because raw daily VIIRS is ~60% cloud over SoCal
  in June; the L4 blend gives clean coverage at a ~10-day science lag
- Updated SPEC-conditions.md and the PDF layout to 4 maps; auto-prune unchanged
```

**Bad:**
```
update report
```

```
fix stuff
```

---

## Repo Documentation Standard (AI-agent-readable)

Every repo ships these so any agent (Claude Code, Cowork, Codex) can use or rebuild it:

- `AGENTS.md` — canonical agent entry point: what the repo is, a **File Map** table
  (`Path | Committed? | Purpose`), the data contract, how it runs, how to extend, privacy
  hard rules, and verification gates.
- `llms.txt` — machine-readable index linking the above.
- `README.md` — human quickstart, features, file table, commands.
- `CLAUDE.md` — project instructions / connectors / known behaviors.
- `BUILD-PLAN.md` — architecture, decisions, and findings.
- `CHANGELOG.md` — Keep a Changelog format, dates in America/Los_Angeles.
- `SPEC-*.md` — the data/interface contract(s).
- `.gitignore` — exclude generated outputs and any real/personal data.

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
