#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PAGINA UNUI APARTAMENT CARE NU O ARE, facuta din fratele lui de acelasi colt.

Andy, 21 aug 2026: *"go pe toate"*, dupa ce i-am aratat ca ap. 18 apare in lista cu pret
(133.000 cu TVA, dat de el in aceeasi zi) dar nu duce nicaieri la click.

DE CE DIN FRATE, SI NU DE LA ZERO. Paginile de apartament sunt scrise de mana si au in ele
lucruri care nu se vad: canonical, sase legaturi hreflang intre limbi, doua blocuri de schema,
firimituri, formular, banda cu termen. Scrisa de la zero, o pagina noua ar rata unul dintre ele
si nimeni n-ar observa pana cand nu s-ar strica ceva. Apartamentele de pe ACELASI COLT au
exact aceeasi impartire: `nr % 4` da coltul, iar 18 si 26 sunt amandoua coltul 2. Deci se ia
pagina fratelui si i se schimba CIFRELE, nu structura.

CE SE SCHIMBA: numarul, etajul, adresa paginii, suprafetele, pretul cu si fara TVA, si toate
locurile in care numarul apare in adrese, in schema si in text. Tot restul ramane bit cu bit.

CE NU FACE: nu inventeaza nimic. Daca o cifra lipseste din date, apartamentul e sarit si spus
pe nume. Si nu suprascrie o pagina existenta: daca folderul e acolo, il lasa in pace.

    python3 pas_pagina_ap.py --repo <cale> --ap 18 --dupa 26
    python3 pas_pagina_ap.py --repo <cale> --ap 18 --dupa 26 --apply
"""
import argparse
import io
import json
import os
import re
import shutil

LIMBI = ["ro", "en", "he", "ar", "uk"]

# cum se scrie etajul in adresa si in text, pe limba
ETAJ_URL = "etaj-%d"


def slug(cam, etaj, nr):
    return "apartament-%d-camere-%s-ap-%s" % (cam, ETAJ_URL % etaj, nr)


def cale_pagina(repo, lb, s):
    baza = repo if lb == "ro" else os.path.join(repo, lb)
    return os.path.join(baza, "apartamente", s, "index.html")


def numar_etaj(e):
    return 0 if e == "parter" else int(e.split()[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--ap", required=True, help="numarul apartamentului fara pagina")
    ap.add_argument("--dupa", required=True, help="numarul fratelui de acelasi colt")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    A = json.load(io.open(os.path.join(a.repo, ".engine", "date", "apartamente.json"),
                          encoding="utf-8"))["apartamente"]
    nou, vechi = A.get(a.ap), A.get(a.dupa)
    if not nou or not vechi:
        print("pas_pagina_ap: nu gasesc apartamentele in date")
        return 1
    if int(a.ap) % 4 != int(a.dupa) % 4:
        print("pas_pagina_ap: ap. %s si ap. %s NU sunt pe acelasi colt (%d contra %d). "
              "Impartirea difera, deci pagina ar minti." %
              (a.ap, a.dupa, int(a.ap) % 4, int(a.dupa) % 4))
        return 1
    for cheie in ("total", "pret", "pret_total", "camere", "etaj"):
        if not nou.get(cheie):
            print("pas_pagina_ap: ap. %s nu are '%s' in date, nu inventez" % (a.ap, cheie))
            return 1

    et_nou, et_vechi = numar_etaj(nou["etaj"]), numar_etaj(vechi["etaj"])
    s_nou = slug(nou["camere"], et_nou, a.ap)
    s_vechi = slug(vechi["camere"], et_vechi, a.dupa)

    # perechile de inlocuit, de la cel mai lung la cel mai scurt: adresele intai, ca sa nu
    # fie ciopartite de inlocuirea numarului simplu care vine dupa
    perechi = [(s_vechi, s_nou)]
    for cheie in ("total", "pret", "pret_total"):
        if vechi.get(cheie) and nou.get(cheie) and vechi[cheie] != nou[cheie]:
            perechi.append((vechi[cheie], nou[cheie]))
    perechi += [
        ("ap-%s" % a.dupa, "ap-%s" % a.ap),
        ("ap. %s" % a.dupa, "ap. %s" % a.ap),
        ("ap. %s" % a.dupa, "ap. %s" % a.ap),
    ]
    if et_nou != et_vechi:
        perechi += [(ETAJ_URL % et_vechi, ETAJ_URL % et_nou),
                    ("Etaj %d" % et_vechi, "Etaj %d" % et_nou),
                    ("etaj %d" % et_vechi, "etaj %d" % et_nou),
                    ("etajul %d" % et_vechi, "etajul %d" % et_nou),
                    ("floor %d" % et_vechi, "floor %d" % et_nou),
                    ("Floor %d" % et_vechi, "Floor %d" % et_nou),
                    ('"floorLevel": "%d"' % et_vechi, '"floorLevel": "%d"' % et_nou)]

    facute, sarite = [], []
    for lb in LIMBI:
        sursa = cale_pagina(a.repo, lb, s_vechi)
        tinta = cale_pagina(a.repo, lb, s_nou)
        if not os.path.exists(sursa):
            sarite.append((lb, "fratele nu are pagina"))
            continue
        if os.path.exists(tinta):
            sarite.append((lb, "pagina exista deja"))
            continue
        h = io.open(sursa, encoding="utf-8").read()
        for v, n in perechi:
            h = h.replace(v, n)
        # controlul: nu are voie sa mai ramana nicio urma a fratelui in adrese
        ramase = len(re.findall(r"ap-%s\b" % a.dupa, h))
        facute.append((lb, tinta, ramase))
        if a.apply:
            os.makedirs(os.path.dirname(tinta), exist_ok=True)
            io.open(tinta, "w", encoding="utf-8", newline="\n").write(h)

    print("pas_pagina_ap: ap. %s dupa ap. %s, %d pagini  (%s)"
          % (a.ap, a.dupa, len(facute), "APLICAT" if a.apply else "PROBA"))
    for lb, t, r in facute:
        print("   %-3s %s%s" % (lb, os.path.relpath(t, a.repo),
                                "   ATENTIE: %d urme ale fratelui" % r if r else ""))
    for lb, de_ce in sarite:
        print("   %-3s SARIT: %s" % (lb, de_ce))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
