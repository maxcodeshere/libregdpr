#!/usr/bin/env python3
"""Parse the Official Journal HTML into structured JSON.

    python3 tools/extract.py [--refresh]

Writes tools/.cache/{DE,EN}_{articles,recitals}.json and prints a census that
should stay identical between the two languages -- the German and English
texts are formatted differently at the source, so agreement is a real signal
that the parse is right.
"""
import json, re, sys, warnings
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# the OJ pages are XHTML; the html parser handles them fine
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from gdpr import CACHE, LANGS, blocks, norm, source_html


def parse(html, prefix):
    soup = BeautifulSoup(html, "lxml")
    res = []
    for el in soup.select(f'div.eli-subdivision[id^="{prefix}_"]'):
        m = re.fullmatch(rf"{prefix}_(\d+)", el.get("id", ""))
        if not m:
            continue
        ti = el.find("p", class_="oj-ti-art")
        sti = el.find("p", class_="oj-sti-art")
        body = []
        for ch in el.find_all(recursive=False):
            cls = ch.get("class") or []
            if (ch.name == "p" and "oj-ti-art" in cls) or "eli-title" in cls:
                continue
            body.extend(blocks(ch if ch.name == "div" else el, 0))
            if ch.name != "div":
                break
        res.append({"n": int(m.group(1)),
                    "ti": norm(ti.get_text()) if ti else None,
                    "st": norm(sti.get_text()) if sti else None,
                    "body": body})
    return sorted(res, key=lambda x: x["n"])


def census(arts):
    kinds = {}
    for a in arts:
        for b in a["body"]:
            if b["k"] != "i":
                continue
            m = b["m"]
            c = ("letter" if re.fullmatch(r"\(?[a-z]\)", m) else
                 "number" if re.fullmatch(r"\(\d+\)|\d+\.", m) else
                 "dash" if re.fullmatch(r"[—–-]", m) else f"OTHER:{m}")
            kinds[c] = kinds.get(c, 0) + 1
            for k in b["kids"]:
                if k["k"] == "i" and re.fullmatch(r"\(?[a-z]\)", k["m"]):
                    kinds["nested:letter"] = kinds.get("nested:letter", 0) + 1
    return kinds


def main():
    refresh = "--refresh" in sys.argv
    CACHE.mkdir(parents=True, exist_ok=True)
    seen = {}
    for lang, L in LANGS.items():
        html = source_html(lang, refresh)
        arts, recs = parse(html, "art"), parse(html, "rct")
        if len(arts) != 99 or len(recs) != 173:
            sys.exit(f"{L}: expected 99 articles and 173 recitals, "
                     f"got {len(arts)} and {len(recs)}")
        (CACHE / f"{L}_articles.json").write_text(json.dumps(arts, ensure_ascii=False), "utf-8")
        (CACHE / f"{L}_recitals.json").write_text(json.dumps(recs, ensure_ascii=False), "utf-8")
        seen[L] = census(arts)
        print(f"{L}: {len(arts)} articles, {len(recs)} recitals, markers {seen[L]}")

    if seen["DE"] != seen["EN"]:
        print("\nWARNING: the two languages disagree on structure:", file=sys.stderr)
        print(f"  DE {seen['DE']}\n  EN {seen['EN']}", file=sys.stderr)
        sys.exit(1)
    print("\nboth languages agree on structure")


if __name__ == "__main__":
    main()
