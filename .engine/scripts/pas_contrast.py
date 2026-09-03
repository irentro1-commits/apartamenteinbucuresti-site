#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CONTRASTUL DIN STILURILE SCRISE IN PAGINA.

Cele mai multe reparatii de contrast s-au facut acolo unde trebuiau, in tokenurile temei
deschise din `pagini-v35.css` si in `carduri-v5.css`. A ramas insa o regula care NU sta
intr-o foaie, ci intr-un `<style>` scris in capul fiecarei pagini, deci nu se poate atinge
dintr-un fisier CSS fara sa te bazezi pe ordinea de incarcare.

CE ERA. `.hlgs2 a`, comutatorul de limba din antet, la `rgba(cerneala, .55)`, adica 3,8:1 pe
crem, sub pragul de 4,5. Se vedea numai pe ecran mare: pe telefon comutatorul sta in panoul
de meniu, care are alta regula. Cinci limbi pe situl asta inseamna ca omul care are nevoie de
comutator e chiar cel care nu citeste romana, si lui ii era cel mai stins element din antet.

DE CE UN PAS SI NU O REGULA IN FOAIE. Un `<style>` scris in pagina bate orice foaie legata
inaintea lui, la specificitate egala. Am platit deja o data lectia asta, cu `stare-v3.css`
incarcata dupa `landing-v2.css`: regula se scrie si nu se aplica. Deci se repara la sursa ei.

    python3 pas_contrast.py --repo <cale>
    python3 pas_contrast.py --repo <cale> --apply
"""
import argparse
import glob
import io
import os

# Fiecare pereche e (forma masurata ca prea deschisa, forma care trece pragul).
# Se scriu intregi, nu prin cautare partiala: o regula CSS prinsa pe bucati e o regula
# schimbata din greseala in alta parte.
PERECHI = [
    # comutatorul de limba din antet: 3,8:1 -> peste prag
    ('.hlgs2 a{color:rgba(var(--cream-rgb),.55);',
     '.hlgs2 a{color:rgba(var(--cream-rgb),.75);'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    atinse = sarite = 0
    for fp in sorted(glob.glob(os.path.join(a.repo, "**", "*.html"), recursive=True)):
        rel = os.path.relpath(fp, a.repo).replace("\\", "/")
        if rel.startswith(".engine/"):
            continue
        h = io.open(fp, encoding="utf-8").read()
        nou = h
        for vechi, pus in PERECHI:
            if vechi in nou:
                nou = nou.replace(vechi, pus)
        if nou == h:
            sarite += 1
            continue
        atinse += 1
        if a.apply:
            io.open(fp, "w", encoding="utf-8", newline="\n").write(nou)

    print("pas_contrast: %d pagini reparate, %d fara ce repara  (%s)"
          % (atinse, sarite, "APLICAT" if a.apply else "PROBA"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
