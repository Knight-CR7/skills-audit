#!/usr/bin/env python3
"""Audit installed Codex skills/plugins for duplicates and overlapping triggers.

Read-only: never deletes or modifies skills. Writes a Markdown report (default
~/.codex/skills-report.md) unless --no-write is given.
"""
import argparse
import difflib
import json
import math
import os
import re
import sys
import time

STOP = set("""a an the and or of to for with this that is are be on in you your it as by from at
into any not do does can should would will if then than like such also using used use when user task
skill skills description name plugin helper helps help work working""".split())

VERBS = ["review", "plan", "debug", "test", "design", "install", "browse", "write", "audit",
         "verify", "brainstorm", "execute", "dispatch", "finish", "create", "convert", "refactor",
         "diagnose", "build", "ship", "release"]


def codex_home():
    return os.environ.get("CODEX_HOME") or os.path.expanduser("~/.codex")


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def frontmatter(text):
    m = re.search(r"^---\s*$(.*?)^---\s*$", text, re.S | re.M)
    return m.group(1) if m else ""


def field(fm, key):
    m = re.search(r"^%s:\s*(.*)$" % key, fm, re.M)
    if not m:
        return ""
    val = m.group(1).strip()
    if val in (">", "|", ">-", "|-"):
        buf = []
        for line in fm[m.end():].splitlines():
            if not line.strip():
                continue
            if line[:1] in (" ", "\t"):
                buf.append(line.strip())
            else:
                break
        val = " ".join(buf)
    return val.strip().strip('"').strip("'")


def tokens(text):
    words = re.findall(r"[a-z][a-z0-9+#.-]{2,}", text.lower())
    return {w for w in words if w not in STOP}


def load_item(path, source, kind):
    text = read_text(path)
    fm = frontmatter(text)
    name = field(fm, "name") or os.path.basename(os.path.dirname(path))
    desc = field(fm, "description") or text[:400]
    return {"name": name, "desc": desc, "path": path, "source": source, "kind": kind}


def load_items(root):
    items = []
    skills_dir = os.path.join(root, "skills")
    if os.path.isdir(skills_dir):
        for name in sorted(os.listdir(skills_dir)):
            p = os.path.join(skills_dir, name, "SKILL.md")
            if os.path.isfile(p):
                items.append(load_item(p, "user", "skill"))
    cache = os.path.join(root, "plugins", "cache")
    if os.path.isdir(cache):
        for market in sorted(os.listdir(cache)):
            mdir = os.path.join(cache, market)
            if not os.path.isdir(mdir):
                continue
            for plugin in sorted(os.listdir(mdir)):
                pdir = os.path.join(mdir, plugin)
                if not os.path.isdir(pdir):
                    continue
                for version in sorted(os.listdir(pdir)):
                    base = os.path.join(pdir, version)
                    pj = os.path.join(base, ".codex-plugin", "plugin.json")
                    if os.path.isfile(pj):
                        meta = {}
                        try:
                            with open(pj, encoding="utf-8") as fh:
                                meta = json.load(fh)
                        except (OSError, ValueError):
                            pass
                        items.append({
                            "name": meta.get("name", plugin),
                            "desc": meta.get("description", ""),
                            "path": pj,
                            "source": "plugin:%s/%s" % (market, plugin),
                            "kind": "plugin",
                        })
                    sdir = os.path.join(base, "skills")
                    if os.path.isdir(sdir):
                        for s in sorted(os.listdir(sdir)):
                            sp = os.path.join(sdir, s, "SKILL.md")
                            if os.path.isfile(sp):
                                items.append(load_item(sp, "plugin:%s/%s" % (market, plugin), "plugin-skill"))
    return items


def tfidf_vectors(docs):
    n = len(docs)
    df = {}
    for toks in docs:
        for t in toks:
            df[t] = df.get(t, 0) + 1
    vecs = []
    for toks in docs:
        v = {t: math.log((n + 1.0) / (df.get(t, 1) + 1.0)) + 1.0 for t in toks}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({t: x / norm for t, x in v.items()})
    return vecs


def cosine(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(w * b.get(t, 0.0) for t, w in a.items())


def one_line(text, limit=90):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit - 1] + "…"


def build_report(items, min_score):
    docs = [tokens(i["desc"]) for i in items]
    vecs = tfidf_vectors(docs)
    lines = []
    lines.append("# Skills Audit Report")
    lines.append("")
    lines.append("- Generated: %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("- Entries: %d (skills %d / plugins %d / bundled skills %d)" % (
        len(items),
        sum(1 for i in items if i["kind"] == "skill"),
        sum(1 for i in items if i["kind"] == "plugin"),
        sum(1 for i in items if i["kind"] == "plugin-skill"),
    ))
    lines.append("")

    lines.append("## 1. Inventory")
    lines.append("")
    lines.append("| Type | Name | Source | Responsibility |")
    lines.append("|---|---|---|---|")
    for it in sorted(items, key=lambda x: (x["kind"], x["name"].lower())):
        lines.append("| %s | `%s` | %s | %s |" % (
            it["kind"], it["name"], it["source"], one_line(it["desc"])))
    lines.append("")

    lines.append("## 2. Duplicate names")
    lines.append("")
    by_name = {}
    for it in items:
        by_name.setdefault(it["name"].lower(), []).append(it)
    def _effective(v):
        own = {x["source"] for x in v if x["kind"] == "plugin-skill"}
        return [x for x in v if not (x["kind"] == "plugin" and x["source"] in own)]
    dupes = {k: _effective(v) for k, v in by_name.items()}
    dupes = {k: v for k, v in dupes.items() if len(v) > 1}
    if dupes:
        for k, v in sorted(dupes.items()):
            lines.append("- `%s` × %d：%s" % (k, len(v), ", ".join("`%s`" % i["path"] for i in v)))
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## 3. Near names")
    lines.append("")
    near = []
    names = list(by_name.keys())
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ratio = difflib.SequenceMatcher(None, a, b).ratio()
            if ratio >= 0.82 and a != b:
                near.append((ratio, a, b))
    near.sort(reverse=True)
    if near:
        for ratio, a, b in near[:15]:
            lines.append("- `%s` ≈ `%s`（%.2f）" % (a, b, ratio))
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## 4. Description similarity")
    lines.append("")
    pairs = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            score = cosine(vecs[i], vecs[j])
            if score >= min_score:
                pairs.append((score, i, j))
    pairs.sort(reverse=True)
    if pairs:
        for score, i, j in pairs[:25]:
            tag = "high confidence" if score >= 0.70 else "needs review"
            lines.append("- **%.2f**（%s）`%s` ⟷ `%s`" % (
                score, tag, items[i]["name"], items[j]["name"]))
    else:
        lines.append("- none (threshold %.2f)" % min_score)
    lines.append("")

    lines.append("## 5. Verb conflicts")
    lines.append("")
    groups = {}
    for it in items:
        for verb in set(tokens(it["desc"])) & set(VERBS):
            groups.setdefault(verb, []).append(it["name"])
    any_group = False
    for verb in sorted(groups):
        names_in = sorted(set(groups[verb]))
        if len(names_in) > 1:
            any_group = True
            lines.append("- `%s`：%s" % (verb, ", ".join("`%s`" % n for n in names_in)))
    if not any_group:
        lines.append("- none")
    lines.append("")

    lines.append("## 6. What to do")
    lines.append("")
    lines.append("1. Start with duplicate names and high-confidence pairs; those are usually clear.")
    lines.append("2. Then review the needs-review pairs and check whether the responsibilities really match.")
    lines.append("3. Keep the narrower, more specific skill; remove or merge the other.")
    lines.append("4. Back up before deleting anything.")
    lines.append("")
    return "\n".join(lines), pairs


def summarize(items, pairs):
    print("Entries: %d" % len(items))
    print("Pairs above threshold: %d" % len(pairs))
    uniq = {i["name"].lower() for i in items}
    print("Distinct names: %d" % len(uniq))


def main():
    ap = argparse.ArgumentParser(description="Audit Codex skills/plugins for overlap.")
    ap.add_argument("--root", default=None, help="CODEX_HOME (default: ~/.codex)")
    ap.add_argument("--out", default=None, help="report path (default: <root>/skills-report.md)")
    ap.add_argument("--min-score", type=float, default=0.55)
    ap.add_argument("--candidate", default=None, help="compare one skill dir against installed ones")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    root = args.root or codex_home()
    items = load_items(root)

    if args.candidate:
        cand_path = os.path.join(args.candidate, "SKILL.md")
        if not os.path.isfile(cand_path):
            print("SKILL.md not found: %s" % cand_path)
            return 2
        cand = load_item(cand_path, "candidate", "skill")
        docs = [tokens(i["desc"]) for i in items]
        vecs = tfidf_vectors(docs + [tokens(cand["desc"])])
        scores = sorted(((cosine(vecs[k], vecs[-1]), items[k]) for k in range(len(items))), key=lambda x: x[0], reverse=True)
        print("Candidate: %s" % cand["name"])
        print("Closest installed items:")
        for score, it in scores[:5]:
            print("  %.2f  %-34s (%s)" % (score, it["name"], it["source"]))
        top = scores[0][0] if scores else 0.0
        if top >= 0.70:
            print("Verdict: heavily overlapping - review before installing.")
        elif top >= 0.55:
            print("Verdict: partial overlap - check the differences first.")
        else:
            print("Verdict: sufficiently distinct - safe to install.")
        return 0

    report, pairs = build_report(items, args.min_score)
    summarize(items, pairs)
    if args.json:
        print(json.dumps({"count": len(items), "pairs": [
            {"score": round(s, 3), "a": items[i]["name"], "b": items[j]["name"]} for s, i, j in pairs
        ]}, ensure_ascii=False, indent=2))
    if not args.no_write:
        out = args.out or os.path.join(root, "skills-report.md")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(report)
        print("Report written: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())