---
name: skills-audit
description: Audit installed Codex skills and plugins for duplicate names, near-identical descriptions, and conflicting trigger words. Use when the user asks whether skills/plugins overlap, before installing a new skill, or when the skill list feels bloated or confusing.
---

# Skills Audit

Scan `$CODEX_HOME/skills` and the plugin cache, then report duplicates and overlapping responsibilities as Markdown. **Read-only — it never deletes anything.**

## When to use

- "Are any of my skills duplicated or conflicting?"
- Before installing a new skill (use `--candidate`)
- When the skill list has grown and you can no longer tell them apart

## Usage

```bash
# Full audit -> ~/.codex/skills-report.md
python ~/.codex/skills/skills-audit/scripts/skills_audit.py

# Before installing: compare a candidate skill directory
python ~/.codex/skills/skills-audit/scripts/skills_audit.py --candidate /path/to/new-skill
```

Windows (PowerShell):

```powershell
python "$env:USERPROFILE\.codex\skills\skills-audit\scripts\skills_audit.py"
python "$env:USERPROFILE\.codex\skills\skills-audit\scripts\skills_audit.py" --candidate "C:\path\to\new-skill"
```

Options: `--out <path>`, `--min-score <float>` (default `0.55`), `--json`, `--no-write`, `--root <CODEX_HOME>`.

## Reading the report

- **Duplicate names** — direct conflict; keep one.
- **Near names** (e.g. `tdd` vs `test-driven-development`) — likely duplicates.
- **Description similarity** — `>= 0.70` suspicious, `0.50-0.70` needs a human look.
- **Verb conflicts** — several skills answering to `review` / `plan` / `debug`; not automatically duplicates, but they compete for triggers.

Similarity is a hint, not a verdict. Skills can share a name yet differ, or differ in name yet overlap. Never delete automatically.