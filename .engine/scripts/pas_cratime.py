#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CUVINTELE CU CRATIMA NU SE MAI RUP IN DOUA, pe tot situl.

Andy, 21 aug 2026, dupa ce a vazut titlul "Etajul 8 · cele doua penthouse-uri, vandute de la
inceput" taiat fix in cratima: *"si nu mai pozitionam textu"*, apoi *"si aplica regula asta de
la penthouse-uri peste tot"*.

DE CE NU CU CRATIMA NEDESPARTITOARE (U+2011), desi ar fi fost o linie de cod.
Situl are 1.743 de aparitii de cuvinte cu cratima, iar cele mai dese sunt **Titan-Dristor**
(350) si **i-vory** (387). "Titan-Dristor" e cuvant-tinta: il vanam in cautare. U+2011 arata
identic pentru om, dar e ALT CARACTER pentru un motor de cautare, si nu exista nicio garantie
ca Google il normalizeaza la cratima obisnuita. Ar fi insemnat sa reparam o problema de
tipografie stricand una de vizibilitate, pe cel mai important cuvant al proiectului.

CE FACE IN LOC: leaga cuvantul cu `white-space: nowrap`, printr-un `<span class="nb">`.
Caracterele raman EXACT aceleasi, deci cautarea, copierea si indexarea nu se schimba cu nimic.
Se schimba doar unde are voie browserul sa rupa randul.

CE NU ATINGE: continutul din `<script>` si `<style>`, valorile atributelor (adresele au si ele
cratime), si tot ce e deja legat. Idempotent: a doua rulare da zero modificari.

    python3 pas_cratime.py --repo <cale>
    python3 pas_cratime.py --repo <cale> --apply
"""
import argparse
import glob
import io
import os
import re

CSS = '<link rel="stylesheet" href="/assets/tipo-v1.css">'
ANCORA_CSS = '<link rel="stylesheet" href="/assets/pagini-v33.css">'

LITERA = "A-Za-zĂÂÎȘȚăâîșț0-9"
# cuvant cu cratima: litera sau cifra de o parte si de alta. Cratima cu spatii in jur e linie
# de dialog sau paranteza, nu cuvant compus, si aceea are voie sa rupa randul.
CUVANT = re.compile(r"[" + LITERA + r"]+(?:-[" + LITERA + r"]+)+")

# blocurile in care nu se intra deloc
SARITE = re.compile(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", re.S)


def leaga_text(t):
    """Leaga in text simplu, deci in afara oricarui tag."""
    return CUVANT.sub(lambda m: '<span class="nb">' + m.group(0) + "</span>", t)


def proceseaza(h):
    if 'class="nb"' in h:
        return h, 0

    # ELEMENTELE CARE NU ACCEPTA MARKUP se sar intregi. `<title>` e text pur: un `<span>`
    # pus acolo se vede LITERAL in fila browserului si in rezultatele Google. Prima versiune
    # a stricat asa 18 titluri, si nu s-ar fi vazut in nicio verificare de taguri: markupul
    # era perfect echilibrat, doar ca ajunsese unde nu are voie sa existe.
    bucati = re.split(
        r"(<script[^>]*>.*?</script>|<style[^>]*>.*?</style>"
        r"|<title>.*?</title>|<textarea[^>]*>.*?</textarea>|<option[^>]*>.*?</option>"
        r"|<[^>]+>)", h, flags=re.S)
    n = 0
    for i, b in enumerate(bucati):
        if not b or b.startswith("<"):
            continue          # tag, script sau stil: nu se atinge nimic
        nou = leaga_text(b)
        if nou != b:
            n += nou.count('class="nb"')
            bucati[i] = nou
    h = "".join(bucati)
    if n and CSS not in h:
        if ANCORA_CSS in h:
            h = h.replace(ANCORA_CSS, ANCORA_CSS + "\n" + CSS, 1)
        else:
            h = h.replace("</head>", CSS + "\n</head>", 1)
    return h, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--doar", default="**/*.html")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    total = fisiere = 0
    for fp in sorted(glob.glob(os.path.join(a.repo, a.doar), recursive=True)):
        if os.path.basename(fp).startswith("_"):
            continue
        h = io.open(fp, encoding="utf-8").read()
        nou, n = proceseaza(h)
        if n:
            total += n
            fisiere += 1
            if a.apply:
                io.open(fp, "w", encoding="utf-8", newline="\n").write(nou)
    print("pas_cratime: %d cuvinte legate in %d fisiere  (%s)"
          % (total, fisiere, "APLICAT" if a.apply else "PROBA"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
