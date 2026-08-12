#!/usr/bin/env python3
"""Turn the extracted Official Journal structure into the project's markdown.

Input is the JSON produced by the extractor: a list of
{n, ti, st, body:[{k:'p'|'i', m, t, kids}]}. Output is the body of the
"Gesetzestext" / "Legal text" section, using the abs/lit/nr shortcodes so that
every Absatz and every Buchstabe is separately linkable.

The text itself is never rewritten -- only wrapped.
"""
import re

# German prints "a)" and "1.", English "(a)" and "(1)". Both map to the same
# shortcode and therefore the same anchor, so a link to #abs-1-lit-f resolves
# in either language; only the printed marker differs (see i18n litMarker).
LETTER = re.compile(r"^\(?([a-z])\)$")
NUMBER = re.compile(r"^(?:\((\d+)\)|(\d+)\.)$")
# DE marks paragraphs "(1) ...", EN marks them "1. ...".
ABSATZ = re.compile(r"^(?:\((\d+)\)|(\d+)\.)\s+(.*)$", re.S)
DASH = re.compile(r"^[—–-]$")


def number_of(marker):
    m = NUMBER.fullmatch(marker)
    return (m.group(1) or m.group(2)) if m else None


def _lit(letter, text, kids):
    inner = [text]
    for k in kids or []:
        if k["k"] == "i" and LETTER.fullmatch(k["m"]):
            inner.append(f'{{{{< lit {LETTER.fullmatch(k["m"]).group(1)} >}}}}{k["t"]}{{{{< /lit >}}}}')
        elif k["k"] == "i":
            inner.append(f'- {k["t"]}')
        else:
            inner.append(k["t"])
    body = "\n".join(inner)
    return f"{{{{< lit {letter} >}}}}{body}{{{{< /lit >}}}}"


def article_markdown(body):
    out, cur = [], None

    def flush():
        nonlocal cur
        if cur is None:
            return
        out.append(f'{{{{< abs {cur["n"]} >}}}}')
        out.extend(cur["lines"])
        out.append("{{< /abs >}}")
        out.append("")
        cur = None

    for b in body:
        if b["k"] == "p":
            m = ABSATZ.match(b["t"])
            if m:
                flush()
                cur = {"n": m.group(1) or m.group(2), "lines": [m.group(3).strip()]}
            elif cur is not None:
                cur["lines"] += ["", b["t"]]
            else:
                out += [b["t"], ""]
            continue

        marker, text, kids = b["m"], b["t"], b.get("kids")

        if LETTER.fullmatch(marker):
            line = _lit(LETTER.fullmatch(marker).group(1), text, kids)
            if cur is not None:
                cur["lines"].append(line)
            else:
                out += [line, ""]
        elif number_of(marker):
            flush()
            no = number_of(marker)
            inner = [text]
            for k in kids or []:
                if k["k"] == "i" and LETTER.fullmatch(k["m"]):
                    inner.append(_lit(LETTER.fullmatch(k["m"]).group(1), k["t"], k.get("kids")))
                elif k["k"] == "i":
                    inner.append(f'- {k["t"]}')
                else:
                    inner.append(k["t"])
            out += [f"{{{{< nr {no} >}}}}" + "\n".join(inner) + "{{< /nr >}}", ""]
        elif DASH.fullmatch(marker):
            line = f"- {text}"
            (cur["lines"] if cur is not None else out).append(line)
        else:
            raise SystemExit(f"unhandled marker {marker!r}")

    flush()
    return "\n".join(out).rstrip() + "\n"


def recital_markdown(body):
    """A recital is a single block; its own number is the page title."""
    parts = []
    for b in body:
        t = b["t"] if b["k"] == "p" else b["t"]
        t = re.sub(r"^\(\d+\)\s*", "", t)
        parts.append(t)
    return "\n\n".join(parts).rstrip() + "\n"
