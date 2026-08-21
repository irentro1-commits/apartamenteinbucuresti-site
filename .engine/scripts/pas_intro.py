#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""INTRODUCEREA DE PE LISTA DE APARTAMENTE: scurta, si cu numarul luat din date.

Andy, 21 aug 2026, cu paragraful pe ecran: *"fa asta, mai taiat la 3 randuri maxim"*.

DOUA DEFECTE INTR-UNUL SINGUR, si al doilea era mai grav decat cel reclamat.

1. Era lung: sapte randuri de intro inaintea listei, cu jumatate din ele repetand ce scrie
   deja in alta parte a paginii (finalizarea e in banda de deasupra, etajele se vad in lista).
2. Numarul de apartamente era SCRIS DE MANA in text. Pe live, romana zicea 7 si ebraica,
   araba si ucraineana ziceau inca **12**: numarul se schimbase, dar numai intr-o limba.
   Un numar scris de mana intr-un text nu ramane adevarat, ramane doar scris.

Acum se numara din `.engine/date/apartamente.json`, aceeasi sursa ca lista de dedesubt, si nu
mai are cum sa se dezalinieze de ea. Pluralul e pe limba: romana are doua forme, ucraineana
trei, araba are si duala, ebraica isi are regula ei.

    python3 pas_intro.py --repo <cale>
    python3 pas_intro.py --repo <cale> --apply
"""
import argparse
import glob
import io
import json
import os
import re

MARCA = 'data-intro="lista"'


def limba(rel):
    for parte in rel.replace("\\", "/").split("/"):
        if parte in ("en", "he", "ar", "uk"):
            return parte
    return "ro"


def cate(T, n):
    """Forma corecta pentru numarul de apartamente ramase, in limba paginii.

    Nu e cosmetica: la romana "1 apartamente" si la ucraineana "5 квартири" sunt greseli pe
    care le vede oricine vorbeste limba, iar textul asta e primul lucru citit pe pagina.
    """
    if n == 1 and T.get("unu"):
        return T["unu"]
    if T.get("putine") and 2 <= (n % 10) <= 4 and not 12 <= (n % 100) <= 14:
        return T["putine"] % n
    return T["multe"] % n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    D = json.load(io.open(os.path.join(a.repo, ".engine", "date", "intro-lista.json"),
                          encoding="utf-8"))
    A = json.load(io.open(os.path.join(a.repo, ".engine", "date", "apartamente.json"),
                          encoding="utf-8"))["apartamente"]
    n = sum(1 for v in A.values() if v["stare"] == "disponibil")

    schimbate, sarite, fara = 0, 0, set()
    for fp in sorted(glob.glob(os.path.join(a.repo, "apartamente", "index.html"))
                     + glob.glob(os.path.join(a.repo, "*", "apartamente", "index.html"))):
        rel = os.path.relpath(fp, a.repo)
        lb = limba(rel)
        T = D["texte"].get(lb)
        if not T:
            fara.add(lb)
            continue
        h = io.open(fp, encoding="utf-8").read()

        # cand a mai ramas UNUL, fraza generala se contrazice singura: "a mai ramas un
        # apartament, majoritatea la etajele 6 si 7". Limbile care au varianta o folosesc.
        sablon = T["corp_unu"] if (n == 1 and T.get("corp_unu")) else T["corp"]
        corp = sablon % {"disp": cate(T, n)}
        nou_p = ('<p class="lead rv" data-fx="rise" %s>%s</p>' % (MARCA, corp))

        # se inlocuieste PARAGRAFUL LEAD, oricare ar fi el: si cel vechi, scris de mana, si
        # cel pus de mine la o rulare anterioara. Garda pe marca singura ar fi lasat pe loc
        # un text cu numarul vechi, exact defectul pe care il repar aici.
        m = re.search(r'<p class="lead[^"]*"[^>]*>.*?</p>', h, re.S)
        if not m:
            sarite += 1
            continue
        if m.group(0) == nou_p:
            sarite += 1
            continue
        h = h[:m.start()] + nou_p + h[m.end():]
        schimbate += 1
        if a.apply:
            io.open(fp, "w", encoding="utf-8", newline="\n").write(h)

    print("pas_intro: %d introduceri rescrise, %d neatinse, %d disponibile  (%s)"
          % (schimbate, sarite, n, "APLICAT" if a.apply else "PROBA"))
    if fara:
        print("   fara text tradus: %s" % ", ".join(sorted(fara)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
