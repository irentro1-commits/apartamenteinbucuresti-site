#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CIFRELE SCRISE DE MASINA, CONTRA DATELOR. Poarta care lipsea pe 27 aug 2026.

DE CE EXISTA. Blocul si-a schimbat numarul de apartamente (33 -> 35) si numarul celor libere
(7 -> 9). Reparatia s-a facut pas cu pas, iar banda de statistici de pe homepage a continuat sa
spuna "7 apartamente disponibile, 20 vandute, 6 rezervate", in toate cele cinci limbi, dupa ce
restul sitului spunea deja 9 din 35. Andy a vazut-o el, nu noi:
*"ba coaie inca apar pe homegape 7 ap disponbile"*.

Cauza nu a fost un pas stricat. `pas_homepage.py` isi lua cifrele corect din date. Cauza a fost
ca NU A FOST RULAT: noua pasi citesc `apartamente.json` si se rulasera doar trei. De aceea
poarta asta nu verifica pasii, ci REZULTATUL.

CE MASOARA, si numai atat: cele patru suprafete scrise de masina, unde cifra are exact un
singur inteles si nu poate fi confundata cu un numar de apartament sau cu un pret.
  1. banda de pe homepage      variabilele --ilr-lib / --ilr-rez / --ilr-vnd si legenda ei
  2. contorul "N <din> M"      in toate cele cinci limbi
  3. CTA-ul "cele N apartamente disponibile"
  4. insignele de stare        starea scrisa pe fiecare card contra starii din date

NU masoara proza. Un text scris de mana care spune o cifra veche nu se prinde aici, si asta e
deliberat: o poarta care da fals pozitive pe fiecare fraza devine o poarta pe care nu o mai
citeste nimeni. Pentru proza, cauta cu grep si repara la sursa.

    python3 gate_numere.py --repo <cale>
"""
import argparse
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LEGATURA = r"(?:din(?:\s+cele)?|out\s+of|of|מתוך|من\s+أصل|من|із|з)"
SP = "[\\s ]*"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    a = ap.parse_args()

    A = json.load(open(os.path.join(ENGINE, "date", "apartamente.json"),
                       encoding="utf-8"))["apartamente"]
    lib = sum(1 for v in A.values() if v["stare"] == "disponibil")
    rez = sum(1 for v in A.values() if v["stare"] == "rezervat")
    vnd = sum(1 for v in A.values() if v["stare"] == "vandut")
    tot = len(A)

    rele = []

    def rau(f, ce, gasit, astept, ctx=""):
        rele.append((os.path.relpath(f, a.repo).replace("\\", "/"), ce, gasit, astept, ctx))

    n = 0
    for fp in sorted(glob.glob(os.path.join(a.repo, "**", "*.html"), recursive=True)):
        rel = os.path.relpath(fp, a.repo).replace("\\", "/")
        if ".engine" in rel.split("/") or os.path.basename(rel).startswith("_proto"):
            # `_proto-*.html` sunt machete, nu pagini livrate: nu sunt in sitemap si
            # nu le vede nimeni. Masurate, dau zgomot care ingroapa defectele reale.
            continue
        n += 1
        s = open(fp, encoding="utf-8").read()

        # 1. banda de pe homepage
        for m in re.finditer(r"--ilr-lib:(\d+);--ilr-rez:(\d+);--ilr-vnd:(\d+)", s):
            g = tuple(int(x) for x in m.groups())
            if g != (lib, rez, vnd):
                rau(fp, "banda homepage", "lib=%d rez=%d vnd=%d" % g,
                    "lib=%d rez=%d vnd=%d" % (lib, rez, vnd))

        # 2. contorul "N <din> M"
        for m in re.finditer(r"(?<![\d.,])(\d{1,3})" + SP + LEGATURA + SP + r"(\d{1,3})(?![\d.,])", s):
            a1, a2 = int(m.group(1)), int(m.group(2))
            # ne uitam doar la perechile care chiar numara blocul: al doilea e un total plauzibil
            if a2 in (tot, 31, 33) or a1 in (lib, 7, 12):
                # "19 din 35" e o propozitie corecta: numara VANDUTELE, nu liberele.
                # Deci prima cifra are voie sa fie oricare dintre cele trei stari.
                if a2 != tot or a1 not in (lib, rez, vnd):
                    rau(fp, "contor", "%d din %d" % (a1, a2), "%d din %d" % (lib, tot),
                        " ".join(s[max(0, m.start() - 40):m.end() + 25].split()))

        # 3. CTA "cele N apartamente disponibile"
        for m in re.finditer(r"cele (?:<b>)?(\d{1,3})(?:[\s ]|&#160;|&nbsp;)+apartamente"
                             r"(?:[\s ]|&#160;|&nbsp;)+disponibile", s):
            if int(m.group(1)) != lib:
                rau(fp, "CTA lista", m.group(1), str(lib))

        # 4. insignele de stare contra datelor, DOAR pe randurile de lista si pe carduri.
        # Un `ap-NN/` gol apare si in canonical, in hreflang si in sitemap, unde nu exista
        # nicio insigna: masurat acolo, orice apartament ar parea "disponibil". Deci se cere
        # explicit un rand sau un card, adica exact locurile unde insigna chiar se scrie.
        for m in re.finditer(r"<a class=\"(?:aprow|card)[^\"]*\"[^>]*ap-(\d+)/\"(.*?)</a>",
                             s, re.S):
            nr, blob = m.group(1), m.group(0)
            if nr not in A:
                rau(fp, "insigna", "ap. %s nu e in date" % nr, "-")
                continue
            asteptat = A[nr]["stare"]
            gasit = ("rezervat" if "e-rezervat" in blob or "stare-rezervat" in blob else
                     "vandut" if "e-vandut" in blob or "stare-vandut" in blob else
                     "disponibil")
            if gasit != asteptat:
                rau(fp, "insigna ap. %s" % nr, gasit, asteptat)

    print("=" * 78)
    print("CIFRELE SCRISE DE MASINA, CONTRA DATELOR")
    print("=" * 78)
    print("  date: %d libere, %d rezervate, %d vandute, %d in total" % (lib, rez, vnd, tot))
    print("  %d pagini masurate" % n)
    if not rele:
        print("  zero cifre in dezacord cu datele.")
        print("  VERDICT: PASS")
        return 0
    print("  %d cifre NU ies din date:" % len(rele))
    for f, ce, g, e, ctx in rele[:30]:
        print("   %-48s %s: %s (asteptat %s)" % (f, ce, g, e))
        if ctx:
            print("        ...%s..." % ctx)
    if len(rele) > 30:
        print("   ... si inca %d" % (len(rele) - 30))
    print("  VERDICT: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
