#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STAREA APARTAMENTELOR pe pagina banilor: insigna de rezervat/vandut si numaratoarea.

DE CE EXISTA. Pe 20 aug 2026 Andy a trimis lista noua a dezvoltatorului: sase apartamente
rezervate, sapte libere. Site-ul le arata pe toate douasprezece ca fiind libere. Un om care
scrie despre un apartament deja rezervat pierde timpul lui si pe al nostru, iar noi pierdem
increderea exact in punctul in care se decide o suma de sase cifre.

SINGURA SURSA DE ADEVAR e `.engine/date/apartamente.json`. Aici nu se scrie nicio stare si nu
se deduce niciuna. Numaratorile din titluri se CALCULEAZA din ea, nu se scriu de mana: o cifra
scrisa de mana intr-un HTML nu se actualizeaza singura si devine minciuna tacuta in ziua in
care se mai vinde unul. Lectia e platita deja, pe cifra de recenzii Google (13 aug 2026).

CE ATINGE, si numai atat:
  · randurile `.prow` de pe /preturi/          insigna + clasa de stare
  · cardurile `.card` de pe /apartamente/      insigna + clasa de stare
  · pagina fiecarui apartament                 insigna sub titlu
  · titlurile care numara                      "N camere · M disponibile", "Etajul X · M disponibile"

Idempotent: rulat de doua ori la rand da zero modificari. Se poate si intoarce, cu --scoate,
fiindca o stare se schimba des si un pas care nu se poate intoarce se aplica cu frica.

    python3 pas_stare.py --repo <cale>            # proba
    python3 pas_stare.py --repo <cale> --apply
    python3 pas_stare.py --repo <cale> --scoate --apply
"""
import argparse
import glob
import json
import os
import re

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open(os.path.join(ENGINE, "date", "apartamente.json"), encoding="utf-8"))
APT = D["apartamente"]
ETICHETE = D["etichete"]

CSS = '<link rel="stylesheet" href="/assets/stare-v2.css">'
ANCORA_CSS = '<link rel="stylesheet" href="/assets/pagini-v33.css">'

# numarul apartamentului se citeste din adresa, nu din text: adresa e stabila, textul nu
NR_DIN_CALE = re.compile(r"-ap-(\d+)/")

ORDINALE = {0: "parter", 1: "etaj 1", 2: "etaj 2", 3: "etaj 3", 4: "etaj 4",
            5: "etaj 5", 6: "etaj 6", 7: "etaj 7"}


def lang_of(h):
    m = re.search(r'<html[^>]*lang="([a-z]{2})"', h)
    return m.group(1) if m and m.group(1) in ETICHETE else "ro"


def insigna(stare, lang):
    if stare not in ("rezervat", "vandut"):
        return ""
    return ('<span class="stare stare-%s">%s</span>' % (stare, ETICHETE[lang][stare]))


def curata(h):
    """Scoate tot ce a pus PASUL ASTA, si numai atat.

    Insignele de «disponibil» NU se ating: ele sunt puse de `pas_lista`, care regenereaza
    lista intreaga din aceleasi date. Prima versiune stergea toate insignele si punea inapoi
    doar rezervat si vandut, fiindca disponibilul nu are insigna pe /preturi/. Rezultat: cele
    sapte etichete verzi de pe /apartamente/ dispareau tacut la fiecare rulare, si s-a vazut
    abia pe live. Doi pasi care scriu in acelasi loc au nevoie de o granita scrisa, nu de
    noroc: aici e granita.
    ORDINEA e pas_lista, apoi pas_stare. Invers, lista ar fi regenerata peste insigne."""
    inc, sf = zona_lista(h)
    cap, mijloc, coada = h[:inc], h[inc:sf], h[sf:]
    def _c(x):
        x = re.sub(r'<span class="stare stare-[a-z]+">[^<]*</span>', "", x)
        x = re.sub(r'<p class="stare-pag">\s*</p>\s*', "", x)
        x = re.sub(r'(<a class="(?:prow|card) rv)( e-(?:rezervat|vandut))', r"\1", x)
        return x
    return _c(cap) + mijloc + _c(coada)


def zona_lista(h):
    """Bucata de pagina care apartine lui `pas_lista`. Nimic din ea nu se atinge aici.

    Fara granita asta, `curata` stergea insignele din lista si `pe_ancora` nu le mai punea
    inapoi, fiindca markupul generat de pas_lista are alta forma (`class="card rv e-rezervat"`
    plus `data-cam` inaintea lui `href`), pe care tiparul de aici nu il prinde. Efectul s-a
    vazut pe LIVE, nu local, si numai fiindca fisierul se scria doar cand se schimba altceva.
    Un pas care se bazeaza pe noroc ca sa nu strice e un pas stricat."""
    i = h.find('id="lista-ap"')
    if i < 0:
        return 0, 0
    j = h.find('id="f-gol"', i)
    return (i, j if j > i else len(h))


def numara(camere=None, etaj=None):
    """Cate sunt LIBERE, dupa filtru. Rezervatul nu e liber: de aceea exista pasul asta."""
    n = 0
    for a in APT.values():
        if a["stare"] != "disponibil":
            continue
        if camere is not None and a["camere"] != camere:
            continue
        if etaj is not None and a["etaj"] != etaj:
            continue
        n += 1
    return n


def scrie_numar(h):
    """Rescrie doar CIFRA din titlurile care numara, si lasa restul frazei neatins."""
    NB = " "

    def cuvant(n):
        """Zero nu se scrie ca cifra. «0 disponibile» arata a eroare de program, nu a
        informatie, si pe pagina banilor asta costa incredere."""
        if n == 0:
            return "niciunul" + NB + "liber"
        return "%d%s%s" % (n, NB, "disponibil" if n == 1 else "disponibile")

    def pe_camere(m):
        cam = int(m.group(1))
        return "%d camere · %s" % (cam, cuvant(numara(camere=cam)))

    def pe_etaj(m):
        cheie = "parter" if m.group(1).lower().startswith("parter") else \
            ORDINALE.get(int(re.sub(r"\D", "", m.group(1)) or -1), None)
        if cheie is None:
            return m.group(0)
        n = numara(etaj=cheie)
        cuv = "disponibil" if n == 1 else "disponibile"
        return "%s · %d%s%s" % (m.group(1), n, NB, cuv)

    def pe_din(m):
        """«12 din 33 disponibile», scris de mana in 39 de locuri. Se schimba doar CIFRA
        LIBERELOR. Totalul ramane neatins, si nu din delicatete: situl scrie 33, iar
        structura reconstituita din plansele dezvoltatorului da 31. Pana nu se lamureste
        care e adevarul, nu ating totalul. O cifra corectata pe jumatate e mai buna decat
        una schimbata pe ghicite."""
        return "%d din %s disponibile" % (numara(), m.group(1))

    def pe_inca(m):
        return "cele %d apartamente încă%sdisponibile" % (numara(), NB)

    h = re.sub(r"\d+ din (\d+)[\s ]*disponibile", pe_din, h)
    h = re.sub(r"cele (<b>)?\d+ apartamente încă[\s ]*disponibile(</b>)?",
               lambda m: "cele %s%d apartamente încă%sdisponibile%s"
               % (m.group(1) or "", numara(), NB, m.group(2) or ""), h)

    h = re.sub(r"(\d) camere ·[\s ]*\d+[\s ]*disponibil[e]?", pe_camere, h)
    h = re.sub(r"(Etajul \d|Parter) ·[\s ]*(?:toate cele )?\d+[\s ]*disponibil[e]?",
               pe_etaj, h)
    return h


def aplica(h, cale_fisier):
    h = curata(h)
    lang = lang_of(h)
    schimbat = [False]

    def pe_ancora(m):
        deschis, href, rest = m.group(1), m.group(2), m.group(3)
        nr = NR_DIN_CALE.search(href)
        if not nr:
            return m.group(0)
        a = APT.get(nr.group(1))
        if not a or a["stare"] == "disponibil":
            return m.group(0)
        schimbat[0] = True
        deschis = deschis + " e-" + a["stare"]
        ins = insigna(a["stare"], lang)
        # insigna intra imediat dupa numarul apartamentului, inainte de <small>
        rest2, n = re.subn(r"(ap\.[\s ]*\d+)(</h3>|<small>|<br)", r"\1" + ins + r"\2",
                           rest, count=1)
        if not n:
            rest2 = re.sub(r"(</h3>|</span>)", ins + r"\1", rest, count=1)
        return '<a class="%s" data-fx="pop" href="%s"%s' % (deschis, href, rest2)

    h = re.sub(r'<a class="((?:prow|card) rv)" data-fx="pop" href="([^"]+)"(.*?)(?=</a>)',
               pe_ancora, h, flags=re.S)

    # pagina proprie a apartamentului: insigna sub titlu
    nr = NR_DIN_CALE.search("/" + cale_fisier.replace(os.sep, "/").rstrip("index.html"))
    if nr:
        a = APT.get(nr.group(1))
        if a and a["stare"] != "disponibil":
            ins = insigna(a["stare"], lang)
            # ATENTIE: sirul de inlocuire NU e brut. Scris ca r"...\"..." baga backslashul
            # in HTML, iese <p class=\"stare-pag\"> si markupul e stricat. Platit pe 20 aug.
            nou = '</h1>\n<p class="stare-pag">' + ins + '</p>'
            h2, n = re.subn("</h1>", nou.replace("\\", "\\\\"), h, count=1)
            if n:
                h = h2
                schimbat[0] = True

    h_nou = scrie_numar(h)
    if h_nou != h:
        h = h_nou
        schimbat[0] = True

    if schimbat[0] and CSS not in h:
        if ANCORA_CSS in h:
            h = h.replace(ANCORA_CSS, ANCORA_CSS + "\n" + CSS, 1)
        else:
            h = h.replace("</head>", CSS + "\n</head>", 1)
    return h, schimbat[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--doar", default="**/*.html")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--scoate", action="store_true", help="doar curata, nu pune nimic")
    a = ap.parse_args()

    n = 0
    for fp in sorted(glob.glob(os.path.join(a.repo, a.doar), recursive=True)):
        h = open(fp, encoding="utf-8").read()
        if a.scoate:
            h2 = curata(h)
            schimbat = h2 != h
        else:
            h2, schimbat = aplica(h, os.path.relpath(fp, a.repo))
        if schimbat and h2 != h:
            n += 1
            if a.apply:
                open(fp, "w", encoding="utf-8", newline="\n").write(h2)

    libere = numara()
    rez = sum(1 for x in APT.values() if x["stare"] == "rezervat")
    vnd = sum(1 for x in APT.values() if x["stare"] == "vandut")
    print("pas_stare: %d fisiere  (%s)" % (n, "APLICAT" if a.apply else "PROBA"))
    print("           %d libere · %d rezervate · %d vandute · %d in total"
          % (libere, rez, vnd, len(APT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
