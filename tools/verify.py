#!/usr/bin/env python3
"""Check the published pages against the Official Journal, word for word.

    hugo --buildDrafts -d public
    python3 tools/verify.py public

Compares the rendered text of every article and every recital, in both
languages, with the source. Whitespace, punctuation and typographic quotes
are normalised away -- the markdown renderer turns a straight apostrophe into
a curly one -- so what remains is a genuine wording difference.

Exit status is non-zero if anything differs, which makes this usable in CI.
"""
import difflib, html, json, pathlib, re, sys, unicodedata

from gdpr import CACHE, ROOT

SECTIONS = {
    "DE": dict(arts="dsgvo", recs="erwaegungsgruende", rec="eg-",
               head="Gesetzestext", nxt="Erwägungsgründe"),
    "EN": dict(arts="en/gdpr", recs="en/recitals", rec="rec-",
               head="Legal text", nxt="Recitals"),
}


def canon(s):
    s = unicodedata.normalize("NFKC", html.unescape(s))
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                 ("–", "-"), ("—", "-"), ("\xa0", " ")):
        s = s.replace(a, b)
    s = re.sub(r"[^0-9A-Za-zÀ-ÿ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def visible(path):
    h = path.read_text(encoding="utf-8")
    a = h[h.find("<article"):h.find("</article>")]
    return re.sub(r"<[^>]+>", " ", a)


def expected(body):
    out = []
    for b in body:
        if b["k"] == "i":
            out.append(b["m"])
        out.append(b["t"])
        out += expected(b.get("kids") or [])
    return out


def main():
    site = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public")
    if not site.is_absolute():
        site = ROOT / site
    if not site.is_dir():
        sys.exit(f"{site} not found -- run hugo --buildDrafts -d {site.name} first")

    fails = []
    for L, cfg in SECTIONS.items():
        arts = {a["n"]: a for a in json.loads((CACHE / f"{L}_articles.json").read_text("utf-8"))}
        recs = {r["n"]: r for r in json.loads((CACHE / f"{L}_recitals.json").read_text("utf-8"))}

        for n, a in arts.items():
            t = visible(site / cfg["arts"] / f"art-{n}" / "index.html")
            i = t.find(cfg["head"])
            j = t.find(cfg["nxt"], i + 1)
            got = canon(t[i + len(cfg["head"]):j if j > 0 else None])
            want = canon(" ".join(expected(a["body"])))
            if want != got:
                fails.append((L, f"Art. {n}", want, got))

        for n, r in recs.items():
            got = canon(visible(site / cfg["recs"] / f'{cfg["rec"]}{n}' / "index.html"))
            want = canon(re.sub(r"^\(\d+\)\s*", "", r["body"][0]["t"]))
            if want not in got:
                fails.append((L, f"Recital {n}", want, got))

    total = sum(len(json.loads((CACHE / f"{L}_{k}.json").read_text("utf-8")))
                for L in SECTIONS for k in ("articles", "recitals"))
    if not fails:
        print(f"{total} pages verified against the Official Journal, no differences")
        return
    print(f"{len(fails)} of {total} pages differ:\n")
    for L, what, want, got in fails[:10]:
        print(f"--- {L} {what}")
        for d in list(difflib.unified_diff(want.split(), got.split(), lineterm="", n=2))[:12]:
            print("   ", d)
    sys.exit(1)


if __name__ == "__main__":
    main()
