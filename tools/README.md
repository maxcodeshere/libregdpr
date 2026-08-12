# Textpipeline

Der Gesetzestext und die Erwägungsgründe werden nicht von Hand gepflegt,
sondern aus dem Amtsblatt erzeugt. Das hält beide Sprachfassungen wortgleich
mit der Quelle und macht ein Korrigendum zu einem nachvollziehbaren Diff
statt zu 544 Einzelbearbeitungen.

Quelle ist die amtliche HTML-Fassung von EUR-Lex, CELEX `32016R0679`.

## Ablauf

```bash
python3 tools/extract.py            # Amtsblatt laden und in JSON zerlegen
python3 tools/generate.py           # Text in die Inhaltsdateien schreiben
hugo --buildDrafts -d public
python3 tools/verify.py public      # gerenderte Seiten gegen die Quelle prüfen
```

`extract.py --refresh` erzwingt einen erneuten Download; sonst wird die
Kopie unter `tools/.cache/` verwendet.

Benötigt `beautifulsoup4` und `lxml`.

## Was die Schritte tun

`extract.py` liest die `div.eli-subdivision`-Blöcke des Amtsblatts. Absätze
sind `p.oj-normal`, Buchstaben und Nummern sind einzeilige Tabellen, deren
erste Zelle die Marke enthält. Am Ende wird gezählt, wie viele Buchstaben,
Nummern und Spiegelstriche gefunden wurden: **beide Sprachfassungen müssen
dieselbe Struktur ergeben**, sonst bricht der Schritt ab. Da die deutsche und
die englische Fassung in der Quelle unterschiedlich ausgezeichnet sind
(`a)` gegenüber `(a)`, `(1)` gegenüber `1.`), ist diese Übereinstimmung ein
echter Hinweis darauf, dass die Zerlegung stimmt.

`convert.py` verpackt Absätze, Buchstaben und die Nummern des Art. 4 in die
Shortcodes `abs`, `lit` und `nr`. Der Text selbst wird nie umgeschrieben, nur
umschlossen. Beide Sprachen benutzen dieselben Anker, damit ein Link auf
`#abs-1-lit-f` in jeder Fassung aufgeht; nur die gedruckte Marke folgt der
jeweiligen amtlichen Schreibweise (siehe `absMarker`, `litMarker`, `nrMarker`
in `i18n/`).

`generate.py` ersetzt ausschließlich den Abschnitt „Gesetzestext“ bzw.
„Legal text“ und den Text der Erwägungsgründe. Überschriften, Front Matter
und die übrigen Abschnitte bleiben unberührt, und ein zweiter Lauf ohne neue
Quelle erzeugt keine Änderung. Weicht eine Artikelüberschrift im Repository
vom Amtsblatt ab, wird das gemeldet, aber nicht stillschweigend geändert.

`verify.py` vergleicht die gerenderten Seiten mit der Quelle. Verglichen wird
nach Normalisierung von Leerraum, Satzzeichen und typografischen Anführungs-
zeichen, sodass nur echte Wortunterschiede übrig bleiben. Der Exit-Code ist
bei Abweichungen ungleich null.

## Bekannte Eigenheiten

Die amtliche deutsche Überschrift von Art. 64 lautet „Stellungnahme
Ausschusses“. Das ist keine Nachlässigkeit im Repository, sondern der Wortlaut
des Amtsblatts; im Text des Artikels steht korrekt „des Ausschusses“.

EUR-Lex beantwortet einfache Skriptanfragen zeitweise mit `202` und leerem
Rumpf. `extract.py` schickt deshalb einen Browser-User-Agent. Falls das nicht
mehr genügt, sind die PDF- und XML-Endpunkte derselben CELEX-Nummer bisher
zugänglicher geblieben.

Goldmark ersetzt gerade Apostrophe durch typografische. Der englische Text
zeigt daher „Member State’s“, wo die Quelle „Member State's“ schreibt. Wer
strikte Zeichentreue will, schaltet `markup.goldmark.extensions.typographer`
ab.
