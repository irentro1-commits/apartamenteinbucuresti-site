#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""INSIGNA LIVE: cand a fost verificata ultima data disponibilitatea, cu ora.

Andy, 21 aug 2026: *"pune si badge live acolo la apartamente si cu ora exacta, sa stie lumea
ca asta e disponibilitatea lor acum si la data asta, verificat cu dezvoltatorul live gen"*.

CE FACE, SI DE CE E O PROMISIUNE CARE SE POATE TINE. Insigna nu spune "acum", spune MOMENTUL,
citit din `.engine/date/apartamente.json`, campul `_verificat.moment`. Momentul ala se schimba
cand cineva chiar intreaba dezvoltatorul, nu la fiecare publicare. Daca s-ar lua ceasul
masinii la build, situl ar scrie vesnic "verificat acum cinci minute" si ar fi o minciuna care
se reinnoieste singura, exact tipul de defect pe care il pazim: un fapt perisabil scris undeva
unde nimeni nu-l mai verifica.

SE STINGE SINGURA. Punctul verde care pulseaza inseamna "proaspat" si apare doar cat
verificarea are sub 48 de ore. Dupa, ramane aceeasi propozitie fara punct si fara pulsatie:
data se vede in continuare, dar nu se mai pretinde ca e de acum. Vechimea se calculeaza LA
GENERARE si se scrie in pagina; pagina fiind statica, nu are cum sa se prefaca mai proaspata
decat e.

    python3 pas_live.py --repo <cale>
    python3 pas_live.py --repo <cale> --apply
"""
import argparse
import datetime
import glob
import io
import json
import os
import re

MARCA = "lv-b"
CSS = '<link rel="stylesheet" href="/assets/live-v1.css">'
ANCORA_CSS = '<link rel="stylesheet" href="/assets/pagini-v33.css">'
PRAG_ORE = 48

LUNI = {
    "ro": ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie", "august",
           "septembrie", "octombrie", "noiembrie", "decembrie"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"],
    "uk": ["січня", "лютого", "березня", "квітня", "травня", "червня", "липня", "серпня",
           "вересня", "жовтня", "листопада", "грудня"],
    "he": ["בינואר", "בפברואר", "במרץ", "באפריל", "במאי", "ביוני", "ביולי", "באוגוסט",
           "בספטמבר", "באוקטובר", "בנובמבר", "בדצמבר"],
    "ar": ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس",
           "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
}

TEXTE = {
    "ro": {"proaspat": "Disponibilitate verificată cu dezvoltatorul",
           "vechi": "Disponibilitate verificată cu dezvoltatorul",
           "la": "%(zi)d %(luna)s, ora %(ora)s"},
    "en": {"proaspat": "Availability checked with the developer",
           "vechi": "Availability checked with the developer",
           "la": "%(zi)d %(luna)s, %(ora)s"},
    "uk": {"proaspat": "Наявність перевірено із забудовником",
           "vechi": "Наявність перевірено із забудовником",
           "la": "%(zi)d %(luna)s, %(ora)s"},
    "he": {"proaspat": "הזמינות נבדקה מול היזם",
           "vechi": "הזמינות נבדקה מול היזם",
           "la": "%(zi)d %(luna)s, %(ora)s"},
    "ar": {"proaspat": "تم التحقق من التوفر مع المطوّر",
           "vechi": "تم التحقق من التوفر مع المطوّر",
           "la": "%(zi)d %(luna)s، %(ora)s"},
}


def limba(rel):
    for parte in rel.replace("\\", "/").split("/"):
        if parte in ("en", "he", "ar", "uk"):
            return parte
    return "ro"


def insigna(lb, mom, proaspat):
    T = TEXTE[lb]
    cand = T["la"] % {"zi": mom.day, "luna": LUNI[lb][mom.month - 1],
                      "ora": mom.strftime("%H:%M")}
    return ('\n<p class="%s%s"><span class="lv-p" aria-hidden="true"></span>'
            '<span class="lv-t">%s <time datetime="%s">%s</time></span></p>\n'
            % (MARCA, " lv-on" if proaspat else "",
               T["proaspat"] if proaspat else T["vechi"],
               mom.isoformat(), cand))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    A = json.load(io.open(os.path.join(a.repo, ".engine", "date", "apartamente.json"),
                          encoding="utf-8"))
    v = A.get("_verificat")
    if not v or not v.get("moment"):
        print("pas_live: nu exista momentul verificarii in date, nu pun nimic")
        return 0
    mom = datetime.datetime.fromisoformat(v["moment"])
    acum = datetime.datetime.now(mom.tzinfo)
    ore = (acum - mom).total_seconds() / 3600.0
    proaspat = 0 <= ore <= PRAG_ORE

    puse = 0
    tinte = (glob.glob(os.path.join(a.repo, "apartamente", "index.html"))
             + glob.glob(os.path.join(a.repo, "*", "apartamente", "index.html"))
             + glob.glob(os.path.join(a.repo, "preturi", "index.html"))
             + glob.glob(os.path.join(a.repo, "*", "preturi", "index.html")))
    for fp in sorted(set(tinte)):
        rel = os.path.relpath(fp, a.repo)
        lb = limba(rel)
        h = io.open(fp, encoding="utf-8").read()
        b = insigna(lb, mom, proaspat)

        # garda: se compara cu ce pun ACUM, nu cu "exista deja o insigna". Ora se schimba,
        # deci o garda pe simpla prezenta ar lasa pe pagina un moment vechi.
        h2 = re.sub(r'\n?<p class="%s[^"]*">.*?</p>\n?' % MARCA, "", h, flags=re.S)
        m = re.search(r'<p class="lead[^"]*"[^>]*>.*?</p>', h2, re.S)
        if not m:
            continue
        nou = h2[:m.end()] + b + h2[m.end():]
        if CSS not in nou:
            nou = (nou.replace(ANCORA_CSS, ANCORA_CSS + "\n" + CSS, 1)
                   if ANCORA_CSS in nou else nou.replace("</head>", CSS + "\n</head>", 1))
        if nou != h:
            puse += 1
            if a.apply:
                io.open(fp, "w", encoding="utf-8", newline="\n").write(nou)

    print("pas_live: %d pagini, verificat acum %.1f ore, punct %s  (%s)"
          % (puse, ore, "aprins" if proaspat else "stins",
             "APLICAT" if a.apply else "PROBA"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
