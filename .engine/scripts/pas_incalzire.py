#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""INCALZIREA NU MERGE PE BALCON, si nu mai scrie nicaieri ca merge.

Andy, 21 aug 2026, verbatim: *"ba si scoate de peste tot incalzire pe balcon ca nu exista
asa ceva, gen stiu ca acum aflu dar plm"*.

CE ERA. Incalzirea in pardoseala e reala si e inclusa in pret, dar NU se intinde pe balcon
si nici pe terasa. Situl afirma contrariul in 130 de fisiere si 235 de locuri, in toate cele
cinci limbi: in listele de dotari, in descrierile meta, in raspunsurile de FAQ din JSON-LD,
in `llms.txt`, si in paragrafe intregi de blog construite pe ideea ca balconul se foloseste
si iarna fiindca e incalzit. Afirmatia venea din materialele dezvoltatorului si o are si
concurenta pe situl ei; asta nu o face adevarata.

DE CE E TABEL, SI NU O EXPRESIE REGULATA. Nu exista un tipar: aceeasi minciuna e scrisa in
douazeci si cinci de feluri pe limba, uneori ca inciza intr-o enumerare, alteori ca argument
al unui paragraf care trebuie rescris ca sa mai curga. Fiecare pereche a fost scrisa de un
editor pe limba lui si contestata de un al doilea, pe fisierele reale.

CAPCANA CARE A PICAT PRIMA VERSIUNE: `pas_asezare` leaga ultimele doua cuvinte ale fiecarui
paragraf cu spatiu NEDESPARTITOR. Sirurile copiate cu spatiu obisnuit nu se gaseau deloc, sau
se gaseau doar in sursa JSON si nu in HTML-ul randat. Perechile de aici sunt taiate inainte
de zona cu nbsp, exact din motivul asta.

SE ATINGE SI SURSA, nu doar HTML-ul: articolele traiesc in `.engine/posts/`, iar daca acolo
ramane textul vechi, prima regenerare a blogului il pune la loc.

    python3 pas_incalzire.py --repo <cale>
    python3 pas_incalzire.py --repo <cale> --apply
"""
import argparse
import glob
import io
import json
import os
import re

# cuvintele care, langa incalzire, arata ca afirmatia inca e acolo
CALD = r"(pardosea|underfloor|תת-רצפתי|أرضية|підлог|חימום|تدفئة|тепла підлога)"
BALC = r"(balcon|balcony|מרפסת|شرفة|балкон)"


def limba(rel):
    p = rel.replace("\\", "/").split("/")
    for parte in p:
        if parte in ("en", "he", "ar", "uk"):
            return parte
    return "ro"


def fisiere(repo):
    for f in sorted(glob.glob(os.path.join(repo, "**", "*.html"), recursive=True)):
        yield f
    for f in sorted(glob.glob(os.path.join(repo, ".engine", "posts", "**", "*.json"),
                              recursive=True)):
        yield f
    t = os.path.join(repo, "llms.txt")
    if os.path.exists(t):
        yield t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    cale = os.path.join(a.repo, ".engine", "date", "incalzire-balcon.json")
    TAB = json.load(io.open(cale, encoding="utf-8"))

    # POTRIVIRE CARE NU SE IMPIEDICA DE SPATII. Doua lucruri strica potrivirea literala:
    # `pas_asezare` leaga ultimele doua cuvinte ale fiecarui element cu spatiu NEDESPARTITOR
    # (U+00A0), iar in sursele JSON apostroful e scapat. Amandoua fac ca un sir copiat corect
    # sa nu se gaseasca nicaieri: prima rulare a acestui pas a ratat asa toate cele 118 perechi
    # de pe romana, desi textul era acolo, cuvant cu cuvant. Deci se cauta cu spatii flexibile.
    def tipar(v):
        buc = re.split(r"[\s\u00a0]+", v)
        return re.compile(r"[\s\u00a0]+".join(re.escape(b) for b in buc if b))

    def leaga_coada(nou, gasit):
        """Daca textul gasit avea ultimele doua cuvinte legate, le leaga si inlocuitorul.

        Altfel am repara continutul si am strica tipografia in acelasi gest: cuvantul de la
        capat s-ar putea rupe pe randul urmator exact acolo unde `pas_asezare` decisese ca nu
        are voie."""
        if "\u00a0" not in gasit or "\u00a0" in nou:
            return nou
        m = list(re.finditer(r"\s(?=[^\s<]+\s*$)", nou))
        if not m:
            return nou
        i = m[-1].start()
        return nou[:i] + "\u00a0" + nou[i + 1:]

    schimbate = locuri = 0
    for fp in fisiere(a.repo):
        rel = os.path.relpath(fp, a.repo)
        lb = limba(rel)
        per = TAB.get(lb, [])
        if fp.endswith("llms.txt"):
            per = [x for lim in TAB.values() for x in lim]   # llms.txt le tine pe toate
        h = io.open(fp, encoding="utf-8").read()
        orig = h
        for x in per:
            t = tipar(x["vechi"])
            gasite = list(t.finditer(h))
            if not gasite:
                continue
            locuri += len(gasite)
            h = t.sub(lambda m: leaga_coada(x["nou"], m.group(0)).replace("\\", "\\\\"), h)
        if h != orig:
            schimbate += 1
            if a.apply:
                io.open(fp, "w", encoding="utf-8", newline="\n").write(h)

    # POARTA. Dupa aplicare, nicaieri in sit nu mai are voie sa apara balconul in vecinatatea
    # incalzirii. Se masoara pe fisiere, nu se presupune din numarul de inlocuiri.
    ramase = []
    if a.apply:
        for fp in fisiere(a.repo):
            h = io.open(fp, encoding="utf-8").read()
            for m in re.finditer(CALD, h, re.I):
                fer = h[max(0, m.start() - 170): m.start() + 240]
                if re.search(BALC, fer, re.I):
                    ramase.append((os.path.relpath(fp, a.repo),
                                   " ".join(re.sub(r"<[^>]+>", " ", fer).split())[:110]))

    print("pas_incalzire: %d fisiere, %d locuri  (%s)"
          % (schimbate, locuri, "APLICAT" if a.apply else "PROBA"))
    if ramase:
        print("\nRAMASE, de citit cu ochiul (balcon langa incalzire):")
        for f, t in ramase[:40]:
            print("   %-58s %s" % (f, t))
        print("   ... total %d" % len(ramase))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
