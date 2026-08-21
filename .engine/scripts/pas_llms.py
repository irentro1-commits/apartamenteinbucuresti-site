#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUPRAFETELE DIN `llms.txt`, aduse la aceeasi sursa ca restul sitului.

Gasit pe 21 aug 2026, in timp ce se scotea afirmatia cu balconul: `llms.txt` tinea inca
suprafetele din GRILA VECHE, cea din iunie. Toate cele 12 apartamente, in toate cele cinci
limbi, deci 60 de cifre gresite: ap. 31 scria 65,9 in loc de 68,15, ap. 30 scria 66,75 in loc
de 58,15. Peste asta, linia parterului trimitea la `apartament-3-camere-parter-ap-2/`, adresa
care da 404: la noi apartamentul de vanzare de la parter e ap. 3.

DE CE CONTEAZA MAI MULT DECAT PARE. `llms.txt` e fisierul pe care il citesc modelele de limbaj
cand raspund despre proiect. O pagina gresita se corecteaza cand o vede cineva; o cifra gresita
de aici se repeta in raspunsurile date de asistenti, fara ca nimeni sa vada de unde vine.

Cifrele nu se mai scriu de mana nicaieri: se citesc din `.engine/date/apartamente.json`,
aceeasi sursa din care se face si lista de pe sit. Formatul liniei si eticheta scrisa de om
raman neatinse; se schimba doar numarul, pretul si adresa.

    python3 pas_llms.py --repo <cale>
    python3 pas_llms.py --repo <cale> --apply
"""
import argparse
import io
import json
import os
import re

# ap. 2 e vandut si nu are pagina; cel de vanzare de la parter e ap. 3. Legatura veche
# ramasese de pe vremea cand numerotarea parterului nu era lamurita.
REDIRECTARI = {"2": "3"}

LINIE = re.compile(
    r"(?P<cap>- \[[^\]]*\]\(https://apartamenteinbucuresti\.ro/)(?P<lb>[a-z]{2}/)?apartamente/"
    r"(?P<slug>[a-z0-9-]+)"
    r"(?P<mij>/\): )"
    r"(?P<supr>[\d.,]+)"
    r"(?P<unit>[^,،]*[,،] )"
    r"(?P<pret>[\d.]+)"
    r"(?P<coada> EUR \+ TVA)")


def zecimal(v, lb):
    """Romana scrie 68,15; celelalte scriu 68.15, asa cum erau deja scrise liniile."""
    return v if lb == "ro" else v.replace(",", ".")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    t = os.path.join(a.repo, "llms.txt")
    if not os.path.exists(t):
        print("pas_llms: nu exista llms.txt")
        return 0
    A = json.load(io.open(os.path.join(a.repo, ".engine", "date", "apartamente.json"),
                          encoding="utf-8"))["apartamente"]
    h = io.open(t, encoding="utf-8").read()

    schimbate, necunoscute = [], []

    def repara(m):
        slug = m.group("slug")
        g = re.search(r"-ap-(\d+)$", slug)
        if not g:
            return m.group(0)
        nr = REDIRECTARI.get(g.group(1), g.group(1))
        v = A.get(nr)
        if not v or not v.get("total"):
            necunoscute.append(g.group(1))
            return m.group(0)
        lb = "ro" if not m.group("lb") else m.group("lb")[:2]
        slug_nou = re.sub(r"-ap-\d+$", "-ap-%s" % nr, slug)
        supr = zecimal(v["total"], lb)
        pret = v.get("pret") or m.group("pret")
        if (supr, pret, slug_nou) != (m.group("supr"), m.group("pret"), slug):
            schimbate.append((nr, m.group("supr"), supr, m.group("pret"), pret))
        # eticheta scrisa de om poate contine si ea numarul vechi
        cap = m.group("cap")
        if nr != g.group(1):
            cap = re.sub(r"(?<=\D)%s(?=\D*\]\()" % g.group(1), nr, cap)
        return (cap + (m.group("lb") or "") + "apartamente/" + slug_nou
                + m.group("mij") + supr + m.group("unit") + pret + m.group("coada"))

    nou = LINIE.sub(repara, h)
    print("pas_llms: %d linii corectate din %d  (%s)"
          % (len(schimbate), len(LINIE.findall(h)), "APLICAT" if a.apply else "PROBA"))
    for nr, sv, sn, pv, pn in schimbate[:14]:
        print("   ap. %-3s  %s -> %s mp   %s -> %s" % (nr, sv, sn, pv, pn))
    if len(schimbate) > 14:
        print("   ... inca %d" % (len(schimbate) - 14))
    if necunoscute:
        print("   fara date, lasate cum erau: %s" % ", ".join(sorted(set(necunoscute))))
    if a.apply and nou != h:
        io.open(t, "w", encoding="utf-8", newline="\n").write(nou)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
