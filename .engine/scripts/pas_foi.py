#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FOILE DE STIL CARE NU AU ALT STAPAN, legate de fiecare pagina.

Nascut pe 21 aug 2026 dintr-o poarta cazuta, nu dintr-o idee. Reparasem telefonul cu o foaie
noua, `landing-v2.css`, si o legasem in pagini cu o bucla scrisa pe loc: 192 de fisiere
atinse direct, fara pas. `verifica_fidelitate.py` a picat imediat cu 65 de fisiere, si avea
dreptate: la prima regenerare, legatura ar fi disparut din toate, iar telefonul s-ar fi
stricat la loc fara ca nimeni sa fi schimbat ceva.

E fix bomba din 10 august 2026, cea din antetul portii: patru randuri de modificari facute
direct in HTML, invizibile din repo, care ar fi murit in tacere la prima rulare automata.
Diferenta e ca de data asta poarta a prins-o in aceeasi ora.

CELELALTE FOI NU SUNT AICI, si asta e regula: fiecare pas isi leaga singur foaia lui.
`pas_terasa` pune `terasa-v2.css`, `pas_live` pune `live-v1.css`, `pas_formular` pune
`formular-v2.css`, `pas_lista` pune `stare-v3.css` si `carduri-v5.css`. Aici stau doar
foile de sit, care nu apartin niciunei lucrari anume.

    python3 pas_foi.py --repo <cale>
    python3 pas_foi.py --repo <cale> --apply
"""
import argparse
import glob
import io
import os

# foaia de reparatii pentru telefon: se aplica pe tot situl, nu doar pe pagina de start
FOI = ["/assets/landing-v2.css"]
ANCORA = '<link rel="stylesheet" href="/assets/pagini-v35.css">'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    puse = aveau = fara_ancora = 0
    for fp in sorted(glob.glob(os.path.join(a.repo, "**", "*.html"), recursive=True)):
        if os.path.basename(fp).startswith("_"):
            continue
        h = io.open(fp, encoding="utf-8").read()
        if ANCORA not in h:
            fara_ancora += 1
            continue
        nou, adaugate = h, 0
        for foaie in FOI:
            link = '<link rel="stylesheet" href="%s">' % foaie
            if link in nou:
                continue
            nou = nou.replace(ANCORA, ANCORA + "\n" + link, 1)
            adaugate += 1
        if not adaugate:
            aveau += 1
            continue
        puse += 1
        if a.apply:
            io.open(fp, "w", encoding="utf-8", newline="\n").write(nou)

    print("pas_foi: %d pagini legate, %d aveau deja, %d fara ancora  (%s)"
          % (puse, aveau, fara_ancora, "APLICAT" if a.apply else "PROBA"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
