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
pe nume.

REPARAT PE 26 AUG 2026, dupa ce prima rulare (ap. 18, 21 aug) a iesit gresit in patru limbi
din cinci. Trei defecte, toate din aceeasi radacina: scriptul stia sa scrie numai romaneste.

  1. CUVANTUL "ETAJ" SI NUMARUL APARTAMENTULUI existau doar in ro si en. Paginile he/ar/uk ale
     lui ap. 18 au ramas integral apartamentul 26: titlu, firimituri, schema si alt spuneau
     "קומה 6 · דירה 26" in loc de "קומה 4 · דירה 18". Acum fiecare limba isi are formele ei,
     in FORME, si se inlocuiesc cu prefix, nu cu cifra goala.

  2. SEPARATORUL ZECIMAL difera: datele scriu "47,05" cu virgula, iar en/he/ar/uk scriu
     suprafata din titlu cu punct, "47.05". Inlocuirea pe virgula nu prindea nimic acolo, deci
     ap. 18 anunta 47.35 mp, suprafata fratelui. Acum se incearca amandoua formele.

  3. INLOCUIREA ETAJULUI IN ADRESE STRICA LEGATURILE CATRE VECINI. Perechea "etaj-6" -> "etaj-4"
     nu se uita la ce urmeaza, deci a rescris si `apartament-2-camere-etaj-6-ap-25` in
     `...-etaj-4-ap-25`, care nu exista: 404 viu, in toate cele cinci limbi. De aceea perechea
     de adresa pe etaj GOL A FOST SCOASA (adresa proprie e acoperita de slugul intreg), iar
     CARDURILE VECINILOR sunt scoase din text inainte de inlocuire si puse la loc dupa. Un card
     descrie ALT apartament: e corect de la sursa si nu are ce cauta in inlocuire.

  4. CONTROLUL MASURA CE NU AVEA CUM SA PICE. Verifica `ap-NN` in adrese, adica exact ce
     repara mereu slugul; a raportat "curat" pe pagini care erau in intregime ale fratelui.
     Acum se verifica numarul SI etajul fratelui in formele limbii, in afara cardurilor, iar
     daca ceva supravietuieste pagina NU se scrie. Se poate forta cu --forta, dar se vede.

    python3 pas_pagina_ap.py --repo <cale> --ap 18 --dupa 26
    python3 pas_pagina_ap.py --repo <cale> --ap 18 --dupa 26 --apply
    python3 pas_pagina_ap.py --repo <cale> --ap 18 --dupa 26 --rescrie --apply   # repara una stricata
"""
import argparse
import io
import json
import os
import re

LIMBI = ["ro", "en", "he", "ar", "uk"]

ETAJ_URL = "etaj-%d"

# Cum scrie fiecare limba etajul, numarul apartamentului si zecimala. Prefixele sunt regex si
# se folosesc ANCORATE inaintea cifrei, ca sa nu se atinga niciodata un numar gol.
FORME = {
    "ro": {"zec": ",", "etaj": [r"[Ee]taj(?:ul)?\s+"], "ap": [r"ap\.\s+"]},
    "en": {"zec": ".", "etaj": [r"[Ff]loor\s+"], "ap": [r"[Aa]pt\.\s+"]},
    "he": {"zec": ".", "etaj": [r"קומה\s+"], "ap": [r"דירה\s+"]},
    "ar": {"zec": ".", "etaj": [r"الطابق\s+"], "ap": [r"شقة\s+رقم\s+", r"الشقة\s+"]},
    "uk": {"zec": ".", "etaj": [r"[Пп]оверх\s+"], "ap": [r"кв\.\s+", r"квартир\w*\s+"]},
}

# Un card e legatura catre ALT apartament. E corect de la sursa, deci se scoate din text cat
# timp se fac inlocuirile si se pune la loc neatins.
CARD = re.compile(r'<a class="card[^"]*"[^>]*>.*?</a>', re.S)


def slug(cam, etaj, nr):
    return "apartament-%d-camere-%s-ap-%s" % (cam, ETAJ_URL % etaj, nr)


def cale_pagina(repo, lb, s):
    baza = repo if lb == "ro" else os.path.join(repo, lb)
    return os.path.join(baza, "apartamente", s, "index.html")


def numar_etaj(e):
    return 0 if e == "parter" else int(e.split()[-1])


def variante(v):
    """Aceeasi cifra cu virgula si cu punct, fiindca limbile nu o scriu la fel."""
    out = {v}
    if "," in v:
        out.add(v.replace(",", "."))
    return out


def scoate_carduri(h):
    pastrate = []

    def _ia(m):
        pastrate.append(m.group(0))
        return "\x00CARD%d\x00" % (len(pastrate) - 1)

    return CARD.sub(_ia, h), pastrate


def pune_carduri(h, pastrate):
    for i, c in enumerate(pastrate):
        h = h.replace("\x00CARD%d\x00" % i, c)
    return h


def prefixate(h, prefixe, vechi, nou):
    """Inlocuieste cifra doar cand e precedata de un prefix cunoscut al limbii."""
    for p in prefixe:
        h = re.sub("(%s)%s(?!\\d)" % (p, re.escape(str(vechi))),
                   lambda m: m.group(1) + str(nou), h)
    return h


def urme(h, prefixe, vechi):
    n = 0
    for p in prefixe:
        n += len(re.findall("%s%s(?!\\d)" % (p, re.escape(str(vechi))), h))
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--ap", required=True, help="numarul apartamentului fara pagina")
    ap.add_argument("--dupa", required=True, help="numarul fratelui de acelasi colt")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rescrie", action="store_true",
                    help="suprascrie o pagina care exista deja (reparatie)")
    ap.add_argument("--forta", action="store_true",
                    help="scrie chiar daca raman urme ale fratelui")
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

    # Perechi valabile in ORICE limba: slugul intreg (care contine si etajul, deci adresa
    # proprie e acoperita), cifrele, si etajul din schema. Adresa pe etaj GOL nu e aici:
    # ar rescrie legaturile catre vecinii de pe acelasi etaj. Vezi defectul 3 din antet.
    comune = [(s_vechi, s_nou)]
    for cheie in ("total", "pret", "pret_total"):
        v, n = vechi.get(cheie), nou.get(cheie)
        if v and n and v != n:
            for vv in sorted(variante(v), key=len, reverse=True):
                comune.append((vv, n if vv == v else n.replace(",", ".")))
    comune.append(("ap-%s" % a.dupa, "ap-%s" % a.ap))
    if et_nou != et_vechi:
        comune.append(('"floorLevel": "%d"' % et_vechi, '"floorLevel": "%d"' % et_nou))

    facute, sarite, murdare = [], [], []
    for lb in LIMBI:
        sursa = cale_pagina(a.repo, lb, s_vechi)
        tinta = cale_pagina(a.repo, lb, s_nou)
        if not os.path.exists(sursa):
            sarite.append((lb, "fratele nu are pagina"))
            continue
        if os.path.exists(tinta) and not a.rescrie:
            sarite.append((lb, "pagina exista deja (--rescrie ca sa o repari)"))
            continue

        h = io.open(sursa, encoding="utf-8").read()
        h, carduri = scoate_carduri(h)
        for v, n in comune:
            h = h.replace(v, n)
        f = FORME[lb]
        h = prefixate(h, f["ap"], a.dupa, a.ap)
        if et_nou != et_vechi:
            h = prefixate(h, f["etaj"], et_vechi, et_nou)

        # CONTROLUL: in afara cardurilor nu are voie sa mai ramana nici numarul fratelui, nici
        # etajul lui, in formele limbii. Plus adresa lui, care e cea mai scumpa greseala.
        r = urme(h, f["ap"], a.dupa) + len(re.findall(r"ap-%s\b" % a.dupa, h))
        if et_nou != et_vechi:
            r += urme(h, f["etaj"], et_vechi)
        h = pune_carduri(h, carduri)

        if r and not a.forta:
            murdare.append((lb, tinta, r))
            continue
        facute.append((lb, tinta, r))
        if a.apply:
            os.makedirs(os.path.dirname(tinta), exist_ok=True)
            io.open(tinta, "w", encoding="utf-8", newline="\n").write(h)

    print("pas_pagina_ap: ap. %s dupa ap. %s, %d pagini  (%s)"
          % (a.ap, a.dupa, len(facute), "APLICAT" if a.apply else "PROBA"))
    for lb, t, r in facute:
        print("   %-3s %s%s" % (lb, os.path.relpath(t, a.repo),
                                "   FORTAT, %d urme" % r if r else ""))
    for lb, t, r in murdare:
        print("   %-3s NESCRIS: %d urme ale ap. %s au supravietuit  (%s)"
              % (lb, r, a.dupa, os.path.relpath(t, a.repo)))
    for lb, de_ce in sarite:
        print("   %-3s SARIT: %s" % (lb, de_ce))
    return 1 if murdare else 0


if __name__ == "__main__":
    raise SystemExit(main())
