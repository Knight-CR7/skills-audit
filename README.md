# skills-audit

Find duplicate and overlapping **Codex skills and plugins** before your skill list turns into soup.

`skills-audit` scans your installed skills plus the plugin cache and produces a Markdown report with:

- **Duplicate names** — the same skill installed twice (e.g. user copy + plugin copy)
- **Near names** — `tdd` vs `test-driven-development`
- **Description similarity** — TF-IDF cosine similarity, noise words filtered
- **Verb conflicts** — several skills all answering to `review`, `plan`, `debug`, …

It is strictly **read-only**: it never deletes or edits a skill. You decide what to keep.

## Why

Skill collections grow fast. Two versions of the same skill, or three skills that all trigger on "review", make the agent slower and less predictable. This gives you a periodic inventory and a pre-install check.

## Install

### Option A — git clone (recommended)

```bash
git clone https://github.com/<owner>/skills-audit.git ~/.codex/skills/skills-audit
```

### Option B — manual copy

Download the repo, then copy the folder so the layout is:

```text
~/.codex/skills/skills-audit/SKILL.md
~/.codex/skills/skills-audit/scripts/skills_audit.py
```

Codex picks up new skills on the next turn (restart the desktop app if it does not).

## Usage

```bash
# Full audit -> ~/.codex/skills-report.md
python ~/.codex/skills/skills-audit/scripts/skills_audit.py

# Before installing something new: compare a candidate directory
python ~/.codex/skills/skills-audit/scripts/skills_audit.py --candidate /path/to/new-skill
```

Windows PowerShell:

```powershell
python "$env:USERPROFILE\.codex\skills\skills-audit\scripts\skills_audit.py"
python "$env:USERPROFILE\.codex\skills\skills-audit\scripts\skills_audit.py" --candidate "C:\path\to\new-skill"
```

### Options

| Flag | Default | Meaning |
|---|---|---|
| `--root` | `~/.codex` | Codex home to scan |
| `--out` | `<root>/skills-report.md` | Report path |
| `--min-score` | `0.55` | Minimum description similarity to report |
| `--candidate` | — | Compare one skill dir against everything installed |
| `--json` | off | Also print machine-readable pairs |
| `--no-write` | off | Print summary only, write no file |

## Sample output

```text
Entries: 74
Pairs above threshold: 14
Distinct names: 53
Report written: C:\Users\me\.codex\skills-report.md
```

The report contains six sections: inventory, duplicate names, near names, description similarity, verb conflicts, and suggested next steps.

## How it works

1. Parse `SKILL.md` frontmatter (`name`, `description`) from `$CODEX_HOME/skills`.
2. Walk `$CODEX_HOME/plugins/cache/<marketplace>/<plugin>/<version>` for `plugin.json` and bundled skills.
3. Build TF-IDF vectors over description tokens (stop words and frontmatter noise removed).
4. Report exact duplicates, `difflib` name similarity ≥ 0.82, cosine similarity ≥ threshold, and shared action verbs.

No third-party dependencies — Python 3.9+ standard library only.

## Limitations

- Similarity is a **hint**, not a verdict. Two skills can share a name but differ in scope.
- Verb conflicts are intentionally noisy: many skills legitimately mention "review" or "create".
- Only reads `SKILL.md` / `plugin.json`; it does not execute or lint skill code.
- Plugin cache layout may change between Codex versions; the walker is defensive but best-effort.

## 中文速览

扫描 `~/.codex/skills` 与插件缓存，输出重复/重叠报告，**只读不删**。

```powershell
python "$env:USERPROFILE\.codex\skills\skills-audit\scripts\skills_audit.py"
python "$env:USERPROFILE\.codex\skills\skills-audit\scripts\skills_audit.py" --candidate "C:\path\to\new-skill"
```

报告：`~/.codex/skills-report.md`。相似度只是线索，最终由你决定保留哪个。

## License

MIT