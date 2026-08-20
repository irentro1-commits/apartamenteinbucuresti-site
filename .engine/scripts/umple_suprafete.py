#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUPRAFETELE LIPSA la apartamentele vandute, luate din acelasi colt al stivei.

DE CE. Cardurile apartamentelor vandute apareau golite: fara pret (corect, nu se pot cumpara)
si fara suprafata (fiindca lipseste din grila dezvoltatorului, care nu mai are cifre pentru ce
s-a vandut demult). In grila, un rand gol langa unul plin arata a scapare, nu a informatie.

Andy, 21 aug 2026: *"stiu ca n-avem mp- dar punem la fel ca ap cu 4 nr de mai sus"*.

REGULA, si nu e o presupunere, e geometria cladirii. Blocul e D+P+7E, cu patru apartamente pe
etaj asezate in jurul casei scarii. Numerele cresc cu 4 de la un etaj la altul, deci acelasi
COLT are acelasi numar modulo 4 si aceeasi compartimentare la toate etajele. Verificarea pe
datele pe care LE AVEM inchide discutia:

    colt 0 (3 camere):  ap. 4 = 84,15   ap. 12 = 84,45   ap. 16 = 84,45   ap. 24 = 85,05
    colt 1 (2 camere):  ap. 17 = 66,70  ap. 21 = 66,70   ap. 25 = 66,85
    colt 2 (2 camere):  ap. 6 = 47,05   ap. 26 = 47,35
    colt 3 (2 camere):  ap. 7 = 60,60   ap. 11 = 60,60   ap. 19 = 60,75  ap. 23 = 60,75  ap. 27 = 60,90

Pe fiecare colt, valorile difera intre ele cu cel mult 90 de centimetri patrati de-a lungul a
sase etaje. Deci suprafata unui apartament necunoscut de pe acelasi colt e cunoscuta cu o
eroare mai mica decat rotunjirea pe care o face oricine cand spune "vreo 60 de metri".

CE NU SE ATINGE, si tot Andy a spus-o: *"parter si et 7 sunt diferite"*.
  · PARTERUL (1, 2, 3) are curte in loc de terasa si numai trei apartamente, nu patru.
  · ETAJUL 7 (28-31) are alte terase si alta impartire pe camere.
Niciunul nu intra in regula si niciunul nu are nevoie: toate sase au deja suprafata.

AP. 18 E SARIT CA SURSA. Suprafata lui (49,20) vine din lista noua a dezvoltatorului si nu se
potriveste cu coltul lui (47,05 la 47,35). Cat timp cifra e in discutie, nu se propaga mai
departe. Se sare peste el si se ia urmatorul de pe acelasi colt.

CE SE SCRIE IN DATE: `total` primeste cifra, dar apar si `total_derivat: true` si `total_sursa`,
ca sa nu se poata confunda niciodata o suprafata dedusa cu una masurata. In pagina nu se vede
nimic din asta: apartamentul e vandut, cifra e context, nu oferta.

    python3 umple_suprafete.py --repo <cale>
    python3 umple_suprafete.py --repo <cale> --apply
"""
import argparse
import io
import json
import os

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALE = os.path.join(ENGINE, "date", "apartamente.json")

# nivelurile care NU respecta stiva: parterul si etajul 7
IN_AFARA_STIVEI = {"parter", "etaj 7"}
# surse in care nu avem incredere azi
SURSE_SARITE = {"18"}
PAS = 4          # patru apartamente pe etaj, deci acelasi colt e din 4 in 4
MAX_NR = 31


def sursa_pentru(nr, A):
    """Urca pe acelasi colt, din 4 in 4, pana gaseste o suprafata in care avem incredere.
    Daca nu gaseste in sus, coboara. Intoarce (numar_sursa, valoare) sau (None, None)."""
    for directie in (PAS, -PAS):
        k = nr + directie
        while 1 <= k <= MAX_NR:
            s = str(k)
            a = A.get(s)
            if a and s not in SURSE_SARITE and a.get("total") \
                    and a["etaj"] not in IN_AFARA_STIVEI \
                    and a["camere"] == A[str(nr)]["camere"]:
                return s, a["total"]
            k += directie
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    d = json.load(io.open(CALE, encoding="utf-8"))
    A = d["apartamente"]

    lipsa = [k for k in sorted(A, key=int)
             if not A[k].get("total") and A[k]["etaj"] not in IN_AFARA_STIVEI]
    puse, ratate = [], []
    for k in lipsa:
        src, val = sursa_pentru(int(k), A)
        if not src:
            ratate.append(k)
            continue
        A[k]["total"] = val
        A[k]["total_derivat"] = True
        A[k]["total_sursa"] = "ap. " + src
        puse.append((k, val, src))

    for k, val, src in puse:
        print("  ap. %-3s -> %s mp   (din ap. %s, acelasi colt)" % (k, val, src))
    if ratate:
        print("  FARA SURSA:", ", ".join(ratate))

    inca = [k for k in sorted(A, key=int) if not A[k].get("total")]
    print("umple_suprafete: %d completate, %d ramase fara suprafata  (%s)"
          % (len(puse), len(inca), "APLICAT" if a.apply else "PROBA"))
    if inca:
        print("  raman:", ", ".join("ap. " + k for k in inca))

    if a.apply and puse:
        io.open(CALE, "w", encoding="utf-8", newline="\n").write(
            json.dumps(d, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
