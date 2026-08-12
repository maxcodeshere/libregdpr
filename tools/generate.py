#!/usr/bin/env python3
"""Write the extracted legal text into the content files.

    python3 tools/extract.py && python3 tools/generate.py

Idempotent: it replaces the legal-text section and the recital body outright,
so re-running after a corrigendum produces a diff containing only what
actually changed in the Official Journal. Nothing outside those two places is
touched -- headings, front matter and the other three sections of an article
are left exactly as they are.
"""
import json, re, sys

from convert import article_markdown, recital_markdown
from gdpr import CACHE, LANGS, ROOT

HEADING = {"de": "Gesetzestext", "en": "Legal text"}
NEXT = {"de": "## Erwägungsgründe", "en": "## Recitals"}


def article_files(lang):
    return {int(p.parent.name): p
            for p in (ROOT / "content" / "dsgvo").rglob(f"index.{lang}.md")}


def split_front_matter(text):
    m = re.match(r"(\+\+\+\n.*?\n\+\+\+\n)(.*)", text, re.S)
    if not m:
        sys.exit("front matter not found")
    return m.group(1), m.group(2)


def main():
    changed = 0
    for lang, L in LANGS.items():
        arts = {a["n"]: a for a in json.loads((CACHE / f"{L}_articles.json").read_text("utf-8"))}
        recs = {r["n"]: r for r in json.loads((CACHE / f"{L}_recitals.json").read_text("utf-8"))}
        files = article_files(lang)
        if len(files) != 99:
            sys.exit(f"{lang}: found {len(files)} article files, expected 99")

        titles = []
        for n, a in arts.items():
            p = files[n]
            s = p.read_text(encoding="utf-8")

            # the heading is authoritative in the repo; report drift, do not fix
            t = re.search(r"^title = ['\"](.+)['\"]$", s, re.M).group(1)
            have = re.sub(r"^(Artikel|Article)\s+\d+\s*-\s*", "", t).strip()
            if a["st"] and have != a["st"]:
                titles.append((n, have, a["st"]))

            head = f"## {HEADING[lang]}\n\n"
            i = s.index(head) + len(head)
            j = s.index(NEXT[lang], i)
            new = s[:i] + article_markdown(a["body"]) + "\n" + s[j:]
            if new != s:
                p.write_text(new, encoding="utf-8")
                changed += 1

        for n, r in recs.items():
            p = ROOT / "content" / "erwaegungsgruende" / f"eg-{n}" / f"index.{lang}.md"
            fm, _ = split_front_matter(p.read_text(encoding="utf-8"))
            new = fm + "\n" + recital_markdown(r["body"])
            if new != p.read_text(encoding="utf-8"):
                p.write_text(new, encoding="utf-8")
                changed += 1

        if titles:
            print(f"{lang}: {len(titles)} title(s) differ from the Official Journal:")
            for n, have, off in titles:
                print(f"   Art. {n}\n     repo:     {have}\n     official: {off}")

    print(f"files changed: {changed}")


if __name__ == "__main__":
    main()
