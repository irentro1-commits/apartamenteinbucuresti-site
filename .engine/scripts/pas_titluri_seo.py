#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TITLURILE META, aduse la forma casei, in toate cele cinci limbi.

Andy, 21 aug 2026: *"sa fie mereu regula sa fie scris frumos 'Apartamente noi de vanzare
Bucuresti | Ansambluri Rezidentiale', gen asa titlul meta seo"*.

Regula intreaga si conditiile masurabile stau in `gate_titluri.py`. Aici se APLICA tabelul
scris de editori si contestat de corectori, `.engine/date/titluri-seo.json`: 105 titluri din
197, adica toate cele care cadeau la poarta.

DE CE TABEL SI NU O REGULA DE INLOCUIRE. Doua puncte se pot schimba in bara cu o expresie
regulata in trei secunde, si ar fi iesit "Bloc nou București, de la Dezvoltator | ce
câștigați": separator corect, titlu prost. Jumatatea de dupa bara trebuie SCRISA, fiindca ea
e prima care se taie in rezultate si trebuie sa fie exact ce se poate pierde. De aceea fiecare
titlu are un om in spate si o justificare in fisierul de date.

Titlul se schimba in trei locuri odata, altfel pagina se contrazice: `<title>`, `og:title` si
`twitter:title`. Se atinge doar unde valoarea veche e IDENTICA cu cea din tabel; daca cineva a
schimbat titlul intre timp, pasul il lasa in pace si il numara la "neatinse".

    python3 pas_titluri_seo.py --repo <cale>
    python3 pas_titluri_seo.py --repo <cale> --apply
"""
import argparse
import io
import json
import os
import re


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    cale = os.path.join(a.repo, ".engine", "date", "titluri-seo.json")
    if not os.path.exists(cale):
        print("pas_titluri_seo: nu exista tabelul, nu ating nimic")
        return 0
    TAB = json.load(io.open(cale, encoding="utf-8"))["titluri"]

    schimbate = neatinse = lipsa = 0
    for rel, t in sorted(TAB.items()):
        fp = os.path.join(a.repo, rel.replace("/", os.sep))
        if not os.path.exists(fp):
            lipsa += 1
            continue
        h = io.open(fp, encoding="utf-8").read()
        m = re.search(r"<title>(.*?)</title>", h, re.S)
        if not m:
            neatinse += 1
            continue
        curent = " ".join(m.group(1).split()).replace(" ", " ")
        if curent == t["nou"]:
            neatinse += 1
            continue
        if curent != t["vechi"]:
            # cineva a schimbat titlul dupa ce s-a scris tabelul: nu se calca peste el
            neatinse += 1
            continue

        nou = h[:m.start(1)] + t["nou"] + h[m.end(1):]
        # og:title si twitter:title poarta acelasi titlu; unde au alta valoare, se lasa
        for prop in ('property="og:title"', 'name="twitter:title"'):
            nou = re.sub(
                r'(<meta [^>]*' + re.escape(prop) + r'[^>]*content=")' + re.escape(t["vechi"]) + r'(")',
                lambda mm: mm.group(1) + t["nou"] + mm.group(2), nou)
            nou = re.sub(
                r'(<meta [^>]*content=")' + re.escape(t["vechi"]) + r'("[^>]*' + re.escape(prop) + r')',
                lambda mm: mm.group(1) + t["nou"] + mm.group(2), nou)
        schimbate += 1
        if a.apply:
            io.open(fp, "w", encoding="utf-8", newline="\n").write(nou)

    print("pas_titluri_seo: %d titluri schimbate, %d neatinse, %d fisiere lipsa  (%s)"
          % (schimbate, neatinse, lipsa, "APLICAT" if a.apply else "PROBA"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
