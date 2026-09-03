#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FEREASTRA DE MODIFICARI LA TERASA, pe fiecare pagina care vinde un apartament.

Andy, 21 aug 2026, verbatim: *"SI PUNE PESTE TOT CA SE POT FACE MODIFICARI LA TERASA DOAR IN
ACEASTA PERIOADA, MAI SUNT 4 LUNI PANA LA PREDARE, IN 2 LUNI NU SE VOR MAI PUTEA FACE
MODIFICARILE ASTEA, GEN CA TERASA SA FIE SUPRAFATA UTILA"*.

CE E, SI DE CE CONTEAZA. E singurul lucru de pe sit care are TERMEN. Restul argumentelor
raman valabile si peste o luna; asta nu. Un om care vede blocul in noiembrie afla ca putea
avea zece metri in plus in casa daca intreba in septembrie, si aia e o discutie pe care nu
vrei sa o ai.

TERMENUL STA INTR-UN SINGUR LOC: `.engine/date/terasa-modificari.json`. Se schimba acolo si
intra in toate cele 60 de pagini. Nu se scrie in text nicaieri altundeva.

CE NU SCRIE, DELIBERAT. Nicio cifra de metri patrati si niciun exemplu numeric. Andy:
*"poate iti dai tu seama ca nu vreau sa zic prostii"*. Din grila nu se poate deduce conversia:
apartamentele cu terasa mica (coltul 2, 7,25 mp) au aproape aceeasi suprafata utila ca cele cu
terasa mare (coltul 3, 21,10 mp), deci diferenta vine din pozitia in bloc, nu dintr-o inchidere.
Cat se inchide si cat rezulta se stabilesc pe planul apartamentului, la vizionare.

UNDE INTRA: pe paginile de apartament, imediat sub plansa, fiindca acolo se vede terasa despre
care e vorba; pe lista de apartamente si pe pagina de preturi, sus, inainte de tabel.

    python3 pas_terasa.py --repo <cale>
    python3 pas_terasa.py --repo <cale> --apply
    python3 pas_terasa.py --repo <cale> --apply --reimprospateaza   # rescrie banda existenta
"""
import argparse
import glob
import io
import json
import os
import re

MARCA = "tz-banda"
CSS = '<link rel="stylesheet" href="/assets/terasa-v2.css">'
ANCORA_CSS = '<link rel="stylesheet" href="/assets/pagini-v35.css">'
WA = "https://wa.me/40774096700"


def limba(rel):
    for parte in rel.replace("\\", "/").split("/"):
        if parte in ("en", "he", "ar", "uk"):
            return parte
    return "ro"


def banda(T, termen, rtl):
    corp = T["corp"] % {"termen": termen}
    return (
        '\n<aside class="%s rv" data-fx="rise"%s>'
        '<span class="tz-c"></span>'
        '<div class="tz-t"><h2>%s</h2><p>%s</p></div>'
        '<a class="tz-b" href="%s" target="_blank" rel="noopener">%s</a>'
        "</aside>\n" % (MARCA, ' dir="rtl"' if rtl else "", T["titlu"], corp, WA, T["cta"]))


def pune(h, b):
    """Sub plansa apartamentului daca exista, altfel dupa primul titlu al paginii.

    Locul nu e ales din comoditate: pe pagina de apartament, terasa despre care vorbim se
    vede in plansa de deasupra, deci anuntul cade exact acolo unde omul se uita la ea.
    """
    i = h.find("</figure>")
    if i > 0:
        j = i + len("</figure>")
        return h[:j] + b + h[j:]
    # Pe lista si pe preturi nu exista plansa, dar exista paragraful de intro. Banda merge
    # DUPA el: intai omul afla ce e pagina, apoi primeste vestea cu ceas. Pusa inainte, sarea
    # peste introducere si pagina incepea cu o avertizare, ceea ce se citeste ca reclama.
    m = re.search(r'<p class="lead[^"]*"[^>]*>.*?</p>', h, re.S)
    if m:
        return h[:m.end()] + b + h[m.end():]
    m = re.search(r"</h1>", h)
    if m:
        # dupa paragraful de intro, daca are unul
        k = h.find("</p>", m.end())
        j = (k + 4) if 0 < k < m.end() + 900 else m.end()
        return h[:j] + b + h[j:]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--reimprospateaza", action="store_true",
                    help="scoate banda veche si o pune la loc, cu textul curent")
    a = ap.parse_args()

    D = json.load(io.open(os.path.join(a.repo, ".engine", "date",
                                       "terasa-modificari.json"), encoding="utf-8"))
    puse = sarite = improspatate = 0
    fara_text = set()

    tinte = []
    for tipar in ("apartamente/*/index.html", "*/apartamente/*/index.html",
                  "apartamente/index.html", "*/apartamente/index.html",
                  "preturi/index.html", "*/preturi/index.html"):
        tinte += glob.glob(os.path.join(a.repo, tipar))

    for fp in sorted(set(tinte)):
        rel = os.path.relpath(fp, a.repo)
        lb = limba(rel)
        T = D["texte"].get(lb)
        if not T:
            fara_text.add(lb)
            continue
        h = io.open(fp, encoding="utf-8").read()

        # GARDA: nu "exista deja ceva", ci "exista exact ce pun eu acum". Un text vechi lasat
        # pe loc fiindca marca era acolo e defectul pe care l-am platit de cinci ori.
        b = banda(T, D["termen"][lb], lb in ("he", "ar"))
        if MARCA in h:
            if not a.reimprospateaza:
                sarite += 1
                continue
            h = re.sub(r'\n?<aside class="%s.*?</aside>\n?' % MARCA, "", h, flags=re.S)
            improspatate += 1

        nou = pune(h, b)
        if nou is None:
            sarite += 1
            continue
        if CSS not in nou:
            nou = (nou.replace(ANCORA_CSS, ANCORA_CSS + "\n" + CSS, 1)
                   if ANCORA_CSS in nou else nou.replace("</head>", CSS + "\n</head>", 1))
        puse += 1
        if a.apply:
            io.open(fp, "w", encoding="utf-8", newline="\n").write(nou)

    print("pas_terasa: %d pagini cu banda, %d improspatate, %d sarite  (%s)"
          % (puse, improspatate, sarite, "APLICAT" if a.apply else "PROBA"))
    if fara_text:
        print("   fara text tradus, nepuse: %s" % ", ".join(sorted(fara_text)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
