#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GATE DE FIDELITATE: ce e in repo trebuie sa fie EXACT ce produce motorul.

    python3 verifica_fidelitate.py --repo /tmp/apt          # exit 1 daca difera ceva

DE CE EXISTA, si e singurul lucru important din fisierul asta.

Pe 10 august 2026 am descoperit ca motorul de blog nu mai putea regenera site-ul. Patru
randuri de modificari se facusera direct in HTML, cu scripturi one-shot din /tmp, si niciuna
nu se intorsese in sursa JSON. Masurat pe o singura pagina, o regenerare pierdea:

    91 spatii nedespartitoare (fixul de orfani, 4 aug)
    blocul de canale de vanzare, intreg (4 aug)
    marca de brand din byline, inlocuita cu cea veche (4 aug)
    suprafata corectata, 84 mp inapoi la 85 (10 aug)

Niciuna nu se vedea din repo, si niciuna nu ar fi dat vreun semn pana in clipa in care
cineva regenera. Adica exact pana in prima noapte de rulare automata.

**Un generator care nu e comparat cu ce e live moare in tacere.** Comparatia nu se poate
face din ochi si nu se poate face "cand ne aducem aminte": se face masinal, la fiecare push.
Asta e tot ce face fisierul asta. Regenereaza intr-o copie si compara octet cu octet.

CAND PICA, ai doua drumuri, si numai unul e corect:
  - ai schimbat SURSA (JSON, scripturi) si diferenta e intentionata -> ruleaza `publica.py`
    pe repo si comite si HTML-ul. Sursa si iesirea merg impreuna, mereu.
  - ai schimbat HTML-ul DIRECT, cu un script one-shot -> intoarce schimbarea in sursa sau
    fa-o un pas din pipeline. Altfel ai reintrodus exact bomba din 10 august.
"""
import argparse, filecmp, os, shutil, subprocess, sys, tempfile, glob

ENGINE = os.path.dirname(os.path.abspath(__file__))
ZONE = ["blog", "en/blog", "he/blog", "ar/blog", "uk/blog"]
FISIERE = ["sitemap.xml", "llms.txt"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--azi", default=None)
    a = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="fidelitate-")
    copie = os.path.join(tmp, "repo")
    # copiem tot repo-ul: motorul isi ia coaja din paginile reale, deci are nevoie de sit intreg
    shutil.copytree(a.repo, copie, ignore=shutil.ignore_patterns(".git"))

    cmd = ["python3", os.path.join(copie, ".engine/scripts/publica.py"), "--repo", copie]
    if a.azi:
        cmd += ["--azi", a.azi]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       env=dict(os.environ, BLOG_REPO=copie,
                                BLOG_POSTS=os.path.join(copie, ".engine/posts")))
    if r.returncode != 0:
        print(r.stdout[-3000:]); print(r.stderr[-2000:], file=sys.stderr)
        print("\nFAIL: motorul nu a rulat pana la capat.")
        return 1

    difera = []
    for z in ZONE:
        for fp in glob.glob(os.path.join(a.repo, z, "**", "index.html"), recursive=True):
            rel = os.path.relpath(fp, a.repo)
            alt = os.path.join(copie, rel)
            if not os.path.exists(alt):
                difera.append((rel, "exista in repo, motorul NU o produce"))
            elif not filecmp.cmp(fp, alt, shallow=False):
                difera.append((rel, "continut diferit"))
        for fp in glob.glob(os.path.join(copie, z, "**", "index.html"), recursive=True):
            rel = os.path.relpath(fp, copie)
            if not os.path.exists(os.path.join(a.repo, rel)):
                difera.append((rel, "motorul o produce, in repo LIPSESTE"))
    for f in FISIERE:
        a1, b1 = os.path.join(a.repo, f), os.path.join(copie, f)
        if os.path.exists(a1) and os.path.exists(b1) and not filecmp.cmp(a1, b1, shallow=False):
            difera.append((f, "continut diferit"))

    shutil.rmtree(tmp, ignore_errors=True)

    if not difera:
        print("FIDELITATE OK: repo-ul e exact ce produce motorul.")
        return 0
    print(f"FIDELITATE PICATA: {len(difera)} fisiere\n")
    for rel, de_ce in difera[:40]:
        print(f"  {de_ce:38} {rel}")
    if len(difera) > 40:
        print(f"  ... inca {len(difera) - 40}")
    print("\nRuleaza `publica.py --repo <repo>` si comite si HTML-ul, SAU intoarce in sursa\n"
          "modificarea facuta direct in HTML. Vezi antetul fisierului asta.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
