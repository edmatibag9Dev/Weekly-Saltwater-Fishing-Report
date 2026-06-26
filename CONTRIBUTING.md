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
