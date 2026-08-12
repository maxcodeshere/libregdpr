#!/usr/bin/env python3
"""Shared bits for the text pipeline: paths, source download, DOM walk.

The pipeline exists so the legal text can be regenerated from the Official
Journal instead of hand-edited -- relevant whenever a corrigendum appears.
"""
import pathlib, re, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "tools" / ".cache"
LANGS = {"de": "DE", "en": "EN"}
CELEX = "32016R0679"
URL = "https://eur-lex.europa.eu/legal-content/{L}/TXT/HTML/?uri=CELEX:" + CELEX

# EUR-Lex answers 202 with an empty body to plain scripted requests. A normal
# browser user agent gets through; if it ever stops working, the PDF and XML
# endpoints for the same CELEX id have proved more permissive.
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def source_html(lang, refresh=False):
    """Official OJ HTML for one language, cached on disk."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{LANGS[lang]}.html"
    if f.exists() and not refresh:
        return f.read_text(encoding="utf-8", errors="replace")
    req = urllib.request.Request(URL.format(L=LANGS[lang]), headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": f"{lang},en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=90) as r:
        body = r.read().decode("utf-8", "replace")
    if "eli-subdivision" not in body:
        sys.exit(f"{lang}: unexpected response from EUR-Lex ({len(body)} bytes); "
                 "the bot check may be active -- retry, or fetch the XML endpoint")
    f.write_text(body, encoding="utf-8")
    return body


def norm(s):
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def blocks(el, depth=0):
    """Paragraphs and marked points, in document order.

    p.oj-normal is a paragraph; a lettered or numbered point is a one-row
    table whose first cell holds the marker and second cell the text.
    """
    out = []
    for ch in el.find_all(recursive=False):
        cls = ch.get("class") or []
        if ch.name == "p" and "oj-normal" in cls:
            t = norm(ch.get_text())
            if t:
                out.append({"k": "p", "d": depth, "t": t})
        elif ch.name == "table":
            body = ch.find("tbody", recursive=False)
            for tr in (body or ch).find_all("tr", recursive=False):
                tds = tr.find_all("td", recursive=False)
                if len(tds) < 2:
                    continue
                sub = blocks(tds[1], depth + 1)
                out.append({
                    "k": "i", "d": depth,
                    "m": norm(tds[0].get_text()),
                    "t": next((x["t"] for x in sub if x["k"] == "p"), ""),
                    "kids": sub[1:],
                })
        elif ch.name == "div":
            out.extend(blocks(ch, depth))
    return out
