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


# -----------------------------------------------------------------------------------------------
# SECTIUNEA «DISPONIBILE», CIFRELE DIN REZUMAT SI TOTALUL BLOCULUI. Adaugat pe 17 sep 2026.
#
# Pasul corecta suprafetele si preturile liniilor care existau, dar nu decidea CARE linii exista.
# Pe 17 sep sectiunea «Apartamente disponibile» lista 14 apartamente, intre ele 3, 4, 12, 19, 25,
# 26, 29, 30 si 31, toate rezervate; lipseau 32 si 34, libere; o linie scria «ap. 26» si ducea la
# ap. 18. Rezumatul spunea «12 apartamente disponibile din 33», in cinci limbi, cu 33 ramas de
# dinainte de 26 aug. Asistentii AI citesc fisierul asta ca adevar si il repeta.
# Acum lista, rezumatul si totalul se scriu din date la fiecare rulare.
L_AP = {
    "ro": ("Apartament %(cam)d camere, %(et)s, ap. %(nr)s", "%(mp)s mp în total, %(pret)s EUR + TVA"),
    "en": ("%(cam)d-Room Apartment, %(et)s, apt. %(nr)s", "%(mp)s sqm total, %(pret)s EUR + TVA"),
    "he": ("%(cam)d חדרים · %(et)s · דירה %(nr)s", "%(mp)s מ״ר בסך הכול, %(pret)s EUR + TVA"),
    "ar": ("%(camar)s · %(et)s · شقة رقم %(nr)s", "%(mp)s م² إجمالي، %(pret)s EUR + TVA"),
    "uk": ("%(cam)d кімнати · %(et)s · кв. %(nr)s", "%(mp)s м² загалом, %(pret)s EUR + TVA"),
}
ETAJ = {
    "ro": ("parter", "etaj %d"), "en": ("Ground Floor", "Floor %d"),
    "he": ("קומת קרקע", "קומה %d"), "ar": ("الطابق الأرضي", "الطابق %d"),
    "uk": ("Партер", "Поверх %d"),
}
PRETURI = {
    "ro": ("2 camere de la %s EUR + TVA", "3 camere de la %s EUR + TVA", "niciun 3 camere liber acum"),
    "en": ("2-room from %s EUR + TVA", "3-room from %s EUR + TVA", "no 3-room available right now"),
    "he": ("2 חדרים מ-%s EUR + TVA", "3 חדרים מ-%s EUR + TVA", "אין כרגע דירות 3 חדרים זמינות"),
    "ar": ("غرفتان من %s EUR + TVA", "3 غرف من %s EUR + TVA", "لا توجد حاليًا شقق 3 غرف متاحة"),
    "uk": ("2-кімнатні від %s EUR + TVA", "3-кімнатні від %s EUR + TVA", "3-кімнатних зараз немає"),
}


def _pret(v):
    return int(v.replace(".", ""))


def sectiunea_disponibile(h, A):
    libere = sorted((k for k, v in A.items() if v["stare"] == "disponibil" and v.get("href")),
                    key=int)
    tot, n = len(A), len(libere)
    preturi = sorted(_pret(A[k]["pret"]) for k in libere if A[k].get("pret"))
    fmt = lambda x: "{:,}".format(x).replace(",", ".")
    randuri = h.split("\n")
    rapoarte = []

    for lb in ("ro", "en", "he", "ar", "uk"):
        pref = "" if lb == "ro" else lb + "/"
        url_pret = "https://apartamenteinbucuresti.ro/%spreturi/)" % pref
        idx = [i for i, r in enumerate(randuri) if url_pret in r]
        if not idx:
            continue
        i = idx[0]
        # linia de preturi: minimul pe tip, numai din ce e liber
        min2 = [_pret(A[k]["pret"]) for k in libere if A[k]["camere"] == 2 and A[k].get("pret")]
        min3 = [_pret(A[k]["pret"]) for k in libere if A[k]["camere"] == 3 and A[k].get("pret")]
        P = PRETURI[lb]
        parti = []
        if min2:
            parti.append(P[0] % fmt(min(min2)))
        parti.append((P[1] % fmt(min(min3))) if min3 else P[2])
        cap = randuri[i][:randuri[i].index(url_pret) + len(url_pret)]
        randuri[i] = cap + ": " + ("; " if lb in ("ro", "en", "uk", "he") else "؛ ").join(parti)

        # blocul de linii de apartament de dupa ea se inlocuieste intreg
        j = i + 1
        while j < len(randuri) and randuri[j].startswith("- [") and "/apartamente/apartament-" in randuri[j]:
            j += 1
        noi = []
        for k in libere:
            v = A[k]
            et = v["etaj"]
            et_txt = ETAJ[lb][0] if et == "parter" else ETAJ[lb][1] % int(et.split()[1])
            eticheta, coada = L_AP[lb]
            d = dict(cam=v["camere"], camar=("غرفتان" if v["camere"] == 2 else "%d غرف" % v["camere"]),
                     et=et_txt, nr=k, mp=zecimal(v["total"], lb), pret=v["pret"])
            noi.append("- [%s](https://apartamenteinbucuresti.ro/%s%s): %s"
                       % (eticheta % d, pref, v["href"].lstrip("/"), coada % d))
        randuri[i + 1:j] = noi
        rapoarte.append("%s: %d linii (erau %d)" % (lb, len(noi), j - i - 1))

    h = "\n".join(randuri)
    lo, hi = (fmt(preturi[0]), fmt(preturi[-1])) if preturi else ("", "")
    ro_n = ("1 apartament disponibil" if n == 1 else
            "%d %sapartamente disponibile" % (n, "de " if n >= 20 else ""))
    uk_n = "квартир" if (tot % 10 in (0, 5, 6, 7, 8, 9) or 11 <= tot % 100 <= 14) else "квартири"
    inlocuiri = [
        # rezumatele de sub titlu
        (r"\d+ (?:de )?apartamente? disponibil[e]? din \d+, prețuri finale [\d.]+-[\d.]+ EUR",
         "%s din %d, prețuri finale %s-%s EUR" % (ro_n, tot, lo, hi)),
        (r"\d+ of \d+ apartments available, final prices [\d.]+-[\d.]+ EUR",
         "%d of %d apartments available, final prices %s-%s EUR" % (n, tot, lo, hi)),
        (r"\d+ מתוך \d+ דירות זמינות, מחירים סופיים [\d.]+-[\d.]+ EUR",
         "%d מתוך %d דירות זמינות, מחירים סופיים %s-%s EUR" % (n, tot, lo, hi)),
        (r"\d+ من أصل \d+ شقة متاحة، أسعار نهائية [\d.]+-[\d.]+ EUR",
         "%d من أصل %d شقة متاحة، أسعار نهائية %s-%s EUR" % (n, tot, lo, hi)),
        (r"\d+ із \d+ квартир[и]? доступні, фінальні ціни [\d.]+-[\d.]+ EUR",
         "%d із %d %s доступні, фінальні ціни %s-%s EUR" % (n, tot, uk_n, lo, hi)),
        # «N din M» de pe linia listei
        (r"(apartamente/\): )\d+ (din|of|מתוך|من أصل|із) \d+",
         lambda m: "%s%d %s %d" % (m.group(1), n, m.group(2), tot)),
        # totalul blocului din «fapte cheie»
        (r"parter \+ 8 etaje, \d+ de apartamente", "parter + 8 etaje, %d de apartamente" % tot),
        (r"ground floor \+ 8 floors, \d+ apartments", "ground floor + 8 floors, %d apartments" % tot),
        (r"קומת קרקע \+ 8 קומות, \d+ דירות", "קומת קרקע + 8 קומות, %d דירות" % tot),
        (r"طابق أرضي \+ 8 طوابق، \d+ شقة", "طابق أرضي + 8 طوابق، %d شقة" % tot),
        (r"партер \+ 8 поверхів, \d+ квартир[и]?", "партер + 8 поверхів, %d %s" % (tot, uk_n)),
    ]
    atinse = 0
    for tipar, pus in inlocuiri:
        h, k = re.subn(tipar, pus, h)
        atinse += k
    return h, rapoarte, atinse


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
    h0 = io.open(t, encoding="utf-8").read()
    h, rapoarte, rez = sectiunea_disponibile(h0, A)
    print("pas_llms: sectiunea disponibile -> %s; rezumat si total: %d locuri"
          % (", ".join(rapoarte), rez))

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
    if a.apply and nou != h0:
        io.open(t, "w", encoding="utf-8", newline="\n").write(nou)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
