#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SCHEMA APARTAMENTULUI, luata din DATE, nu din pagina de langa.

    python3 pas_schema_ap.py --repo <cale>            # arata, nu scrie
    python3 pas_schema_ap.py --repo <cale> --apply

DE CE EXISTA. Pe 24 aug 2026 `gate_graf.py` a picat pagina apartamentului 18 la checkul G7
(afirmatie din schema care nu se gaseste in textul paginii). Masurat, nu presupus:

    schema spunea   floorSize 47.35 mp,  price 107500 EUR
    pagina scria    47,05 mp,            133.000 EUR cu TVA (adica 109.918 fara)
    datele spun     total "47,05",       pret "109.918"     (.engine/date/apartamente.json)

47,35 si 107.500 sunt cifrele apartamentului 26. Pagina lui 18 a fost facuta pe 21 aug de
`pas_pagina_ap.py`, prin clonarea fratelui de pe acelasi colt, iar corectiile de dupa (fisa
dezvoltatorului, pretul dat de Andy in aceeasi zi) au intrat in TEXT si nu in JSON-LD.
Rezultat: Google citea de doua saptamani un pret si o suprafata care nu erau ale nimanui.

    Cand acelasi fapt e scris in doua locuri, unul dintre ele ramane in urma. Aici locurile
    erau textul si schema, iar sursa amandurora e `.engine/date/apartamente.json`.

CE ATINGE, SI DE CE ATAT. Numai campurile care au o singura sursa fara interpretare:
`floorSize.value` din `total` si cele doua `price` din `pret` (fara TVA, cum e scris in
`priceSpecification.valueAddedTaxIncluded: false`). **Nu atinge `availability`.** In date sunt
apartamente cu `"stare": "rezervat"` a caror schema spune `InStock`; e o nepotrivire reala,
dar valoarea corecta e o decizie comerciala (schema.org nu are "rezervat"), deci se raporteaza,
nu se alege de unul singur.

REGULA DE SIGURANTA, aceeasi ca la pas_noduri: un bloc JSON-LD se rescrie numai daca,
nemodificat, se re-serializeaza octet cu octet identic. Altfel pagina e sarita si spusa pe nume.
"""
import argparse
import glob
import json
import os
import re

SCRIPT = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                    re.S | re.I)


def numar(s):
    """'47,05' -> 47.05 ; '109.918' -> 109918 (punctul e separator de mii in romana)."""
    s = str(s).strip()
    if "," in s:
        return float(s.replace(".", "").replace(",", "."))
    return int(s.replace(".", ""))


def incarca_date(engine):
    cale = os.path.join(os.path.dirname(engine), "date", "apartamente.json")
    with open(cale, encoding="utf-8") as f:
        return json.load(f)["apartamente"]


def stil(brut):
    return (", ", ": ") if '", "' in brut or '": "' in brut else (",", ":")


def scrie(d, brut):
    return json.dumps(d, ensure_ascii=False, separators=stil(brut))


def nr_din_cale(rel):
    m = re.search(r"-ap-(\d+)/index\.html$", rel)
    return m.group(1) if m else None


def repara(htm, a):
    """Intoarce (html_nou, [ce s-a schimbat], [avertismente])."""
    facut, atentie = [], []
    supr = numar(a["total"]) if a.get("total") else None
    pret = numar(a["pret"]) if a.get("pret") else None
    if supr is None and pret is None:
        return htm, facut, ["nu are nici total nici pret in date"]

    for m in list(SCRIPT.finditer(htm)):
        brut = m.group(1).strip()
        try:
            d = json.loads(brut)
        except ValueError:
            continue
        tipuri = d.get("@type")
        tipuri = tipuri if isinstance(tipuri, list) else [tipuri]
        if "Apartment" not in tipuri:
            continue
        if scrie(d, brut) != brut:
            atentie.append("blocul Apartment nu se re-serializeaza identic, sarit")
            continue

        schimbari = []
        fs = d.get("floorSize")
        if supr is not None and isinstance(fs, dict) and fs.get("value") != supr:
            schimbari.append("floorSize %s -> %s" % (fs.get("value"), supr))
            fs["value"] = supr
        of = d.get("offers")
        if pret is not None and isinstance(of, dict):
            if of.get("price") != pret:
                schimbari.append("price %s -> %s" % (of.get("price"), pret))
                of["price"] = pret
            ps = of.get("priceSpecification")
            if isinstance(ps, dict) and ps.get("price") != pret:
                schimbari.append("priceSpecification.price %s -> %s" % (ps.get("price"), pret))
                ps["price"] = pret
        if not schimbari:
            continue
        htm = htm[:m.start(1)] + scrie(d, brut) + htm[m.end(1):]
        facut += schimbari
    return htm, facut, atentie


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    engine = os.path.dirname(os.path.abspath(__file__))
    date = incarca_date(engine)

    schimbate, total, toate_atentie, rezervate = 0, 0, [], []
    tipar = os.path.join(a.repo, "**", "apartamente", "*-ap-*", "index.html")
    for cale in sorted(glob.glob(tipar, recursive=True)):
        rel = os.path.relpath(cale, a.repo).replace(os.sep, "/")
        nr = nr_din_cale(rel)
        if nr is None or nr not in date:
            toate_atentie.append("%s: nu gasesc apartamentul in date" % rel)
            continue
        total += 1
        with open(cale, encoding="utf-8") as f:
            htm = f.read()
        nou, facut, atentie = repara(htm, date[nr])
        for w in atentie:
            toate_atentie.append("%s: %s" % (rel, w))
        if date[nr].get("stare") == "rezervat" and '"availability": "https://schema.org/InStock"' in nou:
            rezervate.append(rel)
        if nou == htm:
            continue
        schimbate += 1
        print("  %-62s %s" % (rel, "; ".join(facut)))
        if a.apply:
            with open(cale, "w", encoding="utf-8", newline="") as f:
                f.write(nou)

    for w in toate_atentie:
        print("  ATENTIE  " + w)
    if rezervate:
        print("  DE DECIS  %d pagini au `stare: rezervat` in date si `InStock` in schema."
              % len(rezervate))
        print("            schema.org nu are 'rezervat'; valoarea corecta e decizie comerciala.")
    verb = "reparate" if a.apply else "de reparat (fara --apply nu s-a scris nimic)"
    print("schema apartamentelor: %d pagini %s, din %d citite" % (schimbate, verb, total))
    return 1 if toate_atentie else 0


if __name__ == "__main__":
    raise SystemExit(main())
