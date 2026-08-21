#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""POARTA DE CACHE: ce e in repo trebuie sa fie si ce se serveste.

DE CE EXISTA. `/assets/*` se serveste cu `Cache-Control: public, max-age=31536000, immutable`.
`immutable` e o promisiune facuta browserului si retelei Cloudflare: fisierul asta, la adresa
asta, NU se va schimba niciodata. Cand suprascrii un fisier servit asa, promisiunea se rupe
intr-o singura directie: tu vezi noul fisier pe disc si in git, iar omul primeste in
continuare vechiul, luni de zile. Nu apare nicio eroare. Totul pare desfasurat.

CHITANTA, 21 august 2026. Am reparat contrastul in foaia care se numea atunci
"pagini-v33.css", plus in "carduri-v4.css", am urcat, am verificat ca HTML-ul are formele
noi, si am spus ca e gata. Era gata in repo. Pe live, "pagini-v33.css" avea "Age: 953201",
adica statea in cache de unsprezece zile, cu aurul vechi. Si garda de scroll lateral pusa cu
cateva ore inainte, in "landing-v1.css", n-ajunsese nici ea la nimeni: zero aparitii ale
regulii, pe live. Doua lucrari declarate terminate, niciuna ajunsa la om.

(Numele de mai sus sunt scrise fara prefixul de cale INTENTIONAT: asa nu le mai rescrie
"versioneaza.py" data viitoare, si chitanta ramane citibila peste un an.)

REGULA, SI E SIMPLA. Un fisier servit `immutable` nu se rescrie, i se schimba NUMELE.
Foaia v33 devine v34. Numele e versiunea; asta si inseamna cifra din el.

CE FACE POARTA. Ia fiecare foaie de stil si fiecare script din `/assets/` la care trimite
HTML-ul, il cere de pe live si il compara octet cu octet cu fisierul din repo. Daca difera,
inseamna ca cineva a rescris un fisier servit `immutable`, si poarta cade cu exit 1.

    python3 gate_cache.py --repo <cale>
    python3 gate_cache.py --repo <cale> --gazda https://apartamenteinbucuresti.ro
"""
import argparse
import glob
import io
import os
import re
import sys
import urllib.request

TIPAR = re.compile(r'(?:href|src)="(/assets/[^"?]+\.(?:css|js))"')


def ia(url):
    cerere = urllib.request.Request(url, headers={
        "User-Agent": "gate_cache/1.0 (i-vory, verificare interna)",
        # Fara asta primim raspunsul din cache-ul nostru local si poarta se minte singura.
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    })
    with urllib.request.urlopen(cerere, timeout=30) as r:
        return r.status, r.read(), r.headers.get("Cache-Control", ""), r.headers.get("Age", "-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--gazda", default="https://apartamenteinbucuresti.ro")
    a = ap.parse_args()

    # toate foile la care trimite macar o pagina
    cerute = set()
    for fp in glob.glob(os.path.join(a.repo, "**", "*.html"), recursive=True):
        if os.path.relpath(fp, a.repo).replace("\\", "/").startswith(".engine/"):
            continue
        cerute.update(TIPAR.findall(io.open(fp, encoding="utf-8").read()))

    rele, lipsa, bune = [], [], 0
    for cale in sorted(cerute):
        pe_disc = os.path.join(a.repo, cale.lstrip("/").replace("/", os.sep))
        if not os.path.exists(pe_disc):
            lipsa.append(cale)
            continue
        octeti = io.open(pe_disc, "rb").read()
        try:
            stare, servit, cc, varsta = ia(a.gazda + cale)
        except Exception as e:
            rele.append((cale, "nu s-a putut cere: %s" % str(e)[:60], "-"))
            continue
        if stare != 200:
            rele.append((cale, "live raspunde %s" % stare, "-"))
        elif servit != octeti:
            rele.append((cale, "SE SERVESTE ALTCEVA (%d octeti pe live, %d in repo)"
                         % (len(servit), len(octeti)), varsta))
        else:
            bune += 1

    print("gate_cache: %d foi verificate contra %s" % (len(cerute), a.gazda))
    print("   identice: %d" % bune)
    if lipsa:
        print("   NU EXISTA IN REPO, dar sunt cerute de HTML: %s" % ", ".join(lipsa))
    for cale, motiv, varsta in rele:
        print("   RUPT  %s  %s  (Age: %s)" % (cale, motiv, varsta))
    if rele or lipsa:
        print("\n   Un fisier servit `immutable` nu se rescrie, i se schimba NUMELE.")
        return 1
    print("   CACHE OK: ce e in repo e si ce ajunge la om.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
