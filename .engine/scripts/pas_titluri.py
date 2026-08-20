#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BRANDUL IN FATA, in titlurile care il contin. Si «Dezvoltator» cu majuscula, in titluri.

Andy, 21 aug 2026: *"ce titluri contin Ilioara Residence vreau ca astea sa fie primele 2
cuvinte - nu ultimele + Dezvoltator e scris asa nu cu d mic in titlurile seo"*.

DE CE E MAI MULT DECAT O PREFERINTA. Tot pe 21 august, Andy a aratat ca Google scrie in
rezultate «apartamenteinbucuresti.ro» in loc de «Ilioara Residence», asa cum scrie «Storia»
la storia.ro. Titlul paginii e unul dintre semnalele pe care Google le citeste ca sa aleaga
numele de site, iar un brand pus la COADA, dupa o bara verticala, e cel mai slab loc in care
poate sta. Deci mutarea lui in fata nu e cosmetica: e exact reparatia care sustine cealalta
cerere. Costul, spus pe fata: partea care distinge pagina se muta mai la dreapta si poate fi
taiata de Google pe ecrane mici. Compromisul a fost ales de proprietar, in cunostinta de cauza.

DESPRE MAJUSCULA. Pe 4 august s-a stabilit ca «dezvoltator» se scrie cu litera mica IN PROZA,
fiindca «de la Dezvoltator» in mijlocul unei fraze e greseala de ortografie. Regula aceea
ramane si nu se atinge. Un titlu de pagina nu e proza, e o eticheta, si acolo majuscula e
alegerea proprietarului. Deci: majuscula NUMAI in `<title>`, `og:title` si `twitter:title`.

CE FACE SINGUR: titlurile in care brandul e sufix curat, dupa `|`, `·` sau `–`.
CE NU ATINGE: titlurile in care brandul e prins in mijlocul unei fraze («Echipa Ilioara
Residence: cine construieste...»). Acolo mutarea cere rescrierea frazei, nu taiat si lipit,
si un robot care rescrie titluri de pagina face mai mult rau decat bine. Le RAPORTEAZA.

    python3 pas_titluri.py --repo <cale>
    python3 pas_titluri.py --repo <cale> --apply
"""
import argparse
import glob
import io
import os
import re

BRAND = "Ilioara Residence"
SEPARATOARE = ["|", "·", "–", "—", "-"]

# etichetele in care titlul traieste; toate trei trebuie sa spuna acelasi lucru
CAMPURI = [
    (re.compile(r"(<title>)(.*?)(</title>)", re.S), "title"),
    (re.compile(r'(<meta property="og:title" content=")([^"]*)(")'), "og:title"),
    (re.compile(r'(<meta name="twitter:title" content=")([^"]*)(")'), "twitter:title"),
]


def majuscula_dezvoltator(t):
    """Numai in titluri, si numai cuvantul intreg. «dezvoltatorul» ramane cum e: acolo
    articolul hotarat il face parte de fraza, nu eticheta."""
    return re.sub(r"\bdezvoltator\b", "Dezvoltator", t)


def rearanjeaza(t):
    """Intoarce (titlu_nou, stare). Stari: 'deja', 'mutat', 'de mana', 'fara brand'."""
    if BRAND not in t:
        return t, "fara brand"
    if t.startswith(BRAND):
        return t, "deja"

    for sep in SEPARATOARE:
        # brandul ca sufix curat: "Ceva important | Ilioara Residence"
        coada = sep + " " + BRAND
        if t.endswith(coada):
            rest = t[: -len(coada)].strip()
            if not rest:
                return t, "de mana"
            return BRAND + " " + sep + " " + rest, "mutat"
        # varianta cu spatiu nedespartitor inaintea separatorului
        coada_nb = " " + sep + " " + BRAND
        if t.endswith(coada_nb):
            rest = t[: -len(coada_nb)].strip()
            return BRAND + " " + sep + " " + rest, "mutat"

    # brandul e prins in mijlocul frazei: nu se taie si nu se lipeste automat
    return t, "de mana"


def proceseaza(h):
    schimbari, de_mana = [], []
    for tipar, nume in CAMPURI:
        m = tipar.search(h)
        if not m:
            continue
        vechi = m.group(2).strip()
        nou, stare = rearanjeaza(vechi)
        nou = majuscula_dezvoltator(nou)
        if stare == "de mana":
            de_mana.append((nume, vechi))
        if nou != vechi:
            h = h[: m.start(2)] + nou + h[m.end(2):]
            schimbari.append((nume, vechi, nou))
    return h, schimbari, de_mana


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    atinse = 0
    total = 0
    manual = []
    exemple = []
    for fp in sorted(glob.glob(os.path.join(a.repo, "**", "*.html"), recursive=True)):
        if os.path.basename(fp).startswith("_"):   # fisiere de proba, nu pagini
            continue
        h = io.open(fp, encoding="utf-8").read()
        nou, schimbari, de_mana = proceseaza(h)
        rel = os.path.relpath(fp, a.repo)
        for nume, vechi in de_mana:
            manual.append((rel, nume, vechi))
        if schimbari:
            atinse += 1
            total += len(schimbari)
            if len(exemple) < 8:
                exemple.append((rel, schimbari[0]))
            if a.apply:
                io.open(fp, "w", encoding="utf-8", newline="\n").write(nou)

    for rel, (nume, vechi, nou) in exemple:
        print("  %s" % rel)
        print("    - %s" % vechi)
        print("    + %s" % nou)
    print("pas_titluri: %d campuri schimbate in %d fisiere  (%s)"
          % (total, atinse, "APLICAT" if a.apply else "PROBA"))

    if manual:
        vazut = set()
        print("\nDE MANA, brandul e in mijlocul frazei si mutarea cere rescriere:")
        for rel, nume, vechi in manual:
            if vechi in vazut:
                continue
            vazut.add(vechi)
            print("  [%s] %s" % (nume, vechi))
            print("      %s" % rel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
