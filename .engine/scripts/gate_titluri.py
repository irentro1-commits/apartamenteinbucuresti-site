#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""POARTA TITLURILOR SEO: o singura forma, pe tot situl, in toate limbile.

Andy, 21 aug 2026: *"sa fie mereu regula sa fie scris frumos 'Apartamente noi de vanzare
Bucuresti | Ansambluri Rezidentiale', gen asa titlul meta seo"*.

FORMA: `Frază descriptivă | Calificativ`, cu bara verticala ca SINGUR separator principal.
Nu doua puncte, nu punct median, nu liniuta. Motivul nu e estetica: in rezultatele Google
partea de dupa separator e prima care se taie, deci acolo se pune ce se poate pierde, iar
bara e semnul pe care motoarele si oamenii il citesc drept "aici incepe contextul".

REGULILE, toate masurabile:
  1. exact UN separator ` | `
  2. cel mult 60 de caractere, altfel se taie in rezultate
  3. daca titlul contine numele proiectului, el sta PRIMUL (regula lui Andy, 21 aug: numele
     sa fie primele doua cuvinte, nu ultimele)
  4. amandoua jumatatile incep cu majuscula si niciuna nu e scrisa integral cu majuscule
  5. "Dezvoltator" se scrie cu D mare (regula lui Andy din aceeasi zi)
  6. fara doua puncte, punct median sau liniuta folosite ca separator principal

    python3 gate_titluri.py --repo <cale>
"""
import argparse
import glob
import io
import os
import re
import sys

BRAND = "Ilioara Residence"
LIMITA = 60


def limba(rel):
    for parte in rel.replace("\\", "/").split("/"):
        if parte in ("en", "he", "ar", "uk"):
            return parte
    return "ro"


def verifica(t, lb):
    rele = []
    n = t.count(" | ")
    if n == 0:
        rele.append("fara separator")
    elif n > 1:
        rele.append("%d separatoare" % n)
    if len(t) > LIMITA:
        rele.append("%d caractere" % len(t))
    if BRAND in t and not t.startswith(BRAND):
        rele.append("numele nu e primul")
    if re.search(r"\S:\s|\s·\s|\s-\s|\s—\s", t):
        rele.append("alt separator")
    if lb == "ro" and re.search(r"\bdezvoltator\b", t):
        rele.append("dezvoltator cu d mic")
    for parte in t.split(" | "):
        parte = parte.strip()
        if not parte:
            rele.append("jumatate goala")
            continue
        litere = [c for c in parte if c.isalpha()]
        if litere and all(c.isupper() for c in litere) and len(litere) > 3:
            rele.append("scris cu majuscule")
    return rele


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--limba", default=None)
    a = ap.parse_args()

    total = cazute = 0
    pe_limba = {}
    for f in sorted(glob.glob(os.path.join(a.repo, "**", "*.html"), recursive=True)):
        rel = os.path.relpath(f, a.repo)
        if os.path.basename(rel).startswith("_"):
            continue
        h = io.open(f, encoding="utf-8").read()
        m = re.search(r"<title>(.*?)</title>", h, re.S)
        if not m:
            continue
        t = " ".join(m.group(1).split()).replace("&nbsp;", " ").replace("\u00a0", " ")
        lb = limba(rel)
        if a.limba and lb != a.limba:
            continue
        total += 1
        rele = verifica(t, lb)
        if rele:
            cazute += 1
            pe_limba.setdefault(lb, []).append((rel, t, rele))

    for lb in sorted(pe_limba):
        print("\n--- %s: %d titluri de reparat" % (lb, len(pe_limba[lb])))
        for rel, t, rele in pe_limba[lb][:40]:
            print("   %-58s %s" % (t[:58], ", ".join(rele)))

    print("\ngate_titluri: %d din %d titluri incalca forma" % (cazute, total))
    return 1 if cazute else 0


if __name__ == "__main__":
    sys.exit(main())
