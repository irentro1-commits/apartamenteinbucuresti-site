#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VERSIONEAZA O FOAIE SERVITA `immutable`.

Perechea lui `gate_cache.py`. Poarta spune CA e rupt; asta repara.

CE FACE. Ia o foaie "ceva-vN.css" din assets, o muta in "ceva-v(N+1).css", si rescrie fiecare
trimitere catre ea: in tot HTML-ul si in codul din `.engine/`, fiindca pasii leaga foile pe
nume, iar o rulare urmatoare a motorului ar readuce numele vechi in pagini.

DE CE MUTARE SI NU COPIE. Fisierul vechi ramane servit din cache pentru cine il are deja, dar
nu mai are ce cauta in repo sub numele lui vechi: daca ramane pe disc, urmatoarea reparatie
il rescrie iar si suntem la punctul de plecare. Numele E versiunea.

DE CE SE ATINGE SI `.engine/`. Chitanta: `pas_lista.py`, `pas_terasa.py` si `pas_foi.py` isi
leaga fiecare foaia pe nume, scris in cod. Redenumita doar in pagini, primul `publica.py` ar
fi pus la loc numele vechi si poarta de fidelitate ar fi cazut.

    python3 versioneaza.py --repo <cale> ceva-v3.css altceva-v1.css
    python3 versioneaza.py --repo <cale> --apply ceva-v3.css altceva-v1.css
"""
import argparse
import glob
import io
import os
import re
import shutil

TIPAR_V = re.compile(r"^(?P<baza>.+?)-v(?P<n>\d+)\.(?P<ext>css|js)$")


def urmatorul(nume):
    m = TIPAR_V.match(nume)
    if not m:
        raise SystemExit("nu stiu sa versionez %r: numele trebuie sa fie forma <ceva>-v<N>.css"
                         % nume)
    return "%s-v%d.%s" % (m.group("baza"), int(m.group("n")) + 1, m.group("ext"))


def fisiere_de_atins(repo):
    """Tot HTML-ul din sit, plus codul din .engine (pasii leaga foile pe nume).

    NU se ating `.md` si `.txt`: acolo nu stau legaturi, ci explicatii. Vezi de ce, mai jos.
    """
    for f in glob.glob(os.path.join(repo, "**", "*.html"), recursive=True):
        yield f
    for tipar in ("**/*.py", "**/*.json"):
        for f in glob.glob(os.path.join(repo, ".engine", tipar), recursive=True):
            yield f


def rescrie(text, vechi, nou):
    """Rescrie NUMAI caile reale, `/assets/<nume>`, nu si numele scris in proza.

    CHITANTA, si e din prima rulare a uneltei astea. Am rescris orice aparitie a numelui,
    oriunde. Rezultatul: comentariile care EXPLICAU mutarea au ajuns sa spuna "ia foaia
    v34 si mut-o in v34", iar poarta care documenta defectul si-a pierdut chitanta, fiindca
    numele vechi, cel care dovedea ce s-a intamplat, a fost inlocuit cu cel nou. O unealta
    care isi rescrie propria explicatie sterge exact lucrul pentru care a fost scrisa.

    Legaturile au intotdeauna prefixul `/assets/`. Proza scrie numele gol, intre accente
    grave. Deci se rescrie doar ce are prefixul, si explicatiile raman intregi.
    """
    return text.replace("/assets/" + vechi, "/assets/" + nou)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("foi", nargs="+", help="numele fisierelor din assets/, ex: ceva-v3.css")
    a = ap.parse_args()

    perechi = []
    for nume in a.foi:
        vechi = os.path.join(a.repo, "assets", nume)
        if not os.path.exists(vechi):
            raise SystemExit("nu exista: %s" % vechi)
        nou = urmatorul(nume)
        if os.path.exists(os.path.join(a.repo, "assets", nou)):
            raise SystemExit("exista deja %s: alege alt pas de versiune" % nou)
        perechi.append((nume, nou))
        print("  %s  ->  %s" % (nume, nou))

    atinse = 0
    for fp in sorted(set(fisiere_de_atins(a.repo))):
        try:
            h = io.open(fp, encoding="utf-8").read()
        except (UnicodeDecodeError, PermissionError):
            continue
        nou_h = h
        for vechi, nou in perechi:
            nou_h = rescrie(nou_h, vechi, nou)
        if nou_h == h:
            continue
        atinse += 1
        if a.apply:
            io.open(fp, "w", encoding="utf-8", newline="\n").write(nou_h)

    if a.apply:
        for vechi, nou in perechi:
            shutil.move(os.path.join(a.repo, "assets", vechi),
                        os.path.join(a.repo, "assets", nou))

    print("versioneaza: %d fisiere cu trimiteri rescrise, %d foi mutate  (%s)"
          % (atinse, len(perechi) if a.apply else 0, "APLICAT" if a.apply else "PROBA"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
