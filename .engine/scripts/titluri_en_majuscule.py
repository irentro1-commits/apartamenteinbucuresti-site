#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aduce titlurile ENGLEZESTI la Title Case, ca sa nu mai fie doua conventii pe acelasi site.

Andy, 13 Aug 2026: *"si vezi ca me ta titlurile in engleza si paote si in alte limbi striane sunt
scrise cu litera mica boss"*.

STAREA MASURATA inainte: 24 din 37 de titluri EN erau deja Title Case (paginile de produs si de
meniu), iar 13 erau sentence case (homepage-ul si toate cele 12 articole de blog). Nu era o
alegere, era o cusatura intre doua loturi scrise in momente diferite.

NUMAI ENGLEZA, si asta e important:
  - ucraineana NU foloseste Title Case. Majuscula pe fiecare cuvant e greseala de ortografie
    acolo, deci `uk/` ramane neatins, cu sentence case, cum e corect.
  - ebraica si araba nu au majuscule ca sistem de scriere. Intrebarea nu se pune.
  - romana foloseste tot sentence case.

REGULA: se capitalizeaza cuvintele principale. Raman mici articolele, conjunctiile si prepozitiile
scurte, MAI PUTIN cand sunt primul cuvant, ultimul cuvant, sau imediat dupa `:` ori `|`.
Acronimele si unitatile scrise deja cu majuscule (VAT, IOR, EUR, TVA) nu se ating. Cuvintele
compuse cu cratima se capitalizeaza pe ambele parti (`new-build` -> `New-Build`), fiindca asa erau
deja scrise titlurile bune de pe site (`New-Build Apartments`).

Idempotent: rulat de doua ori nu schimba nimic. `--dry` simuleaza.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
DRY = '--dry' in sys.argv

MICI = {
    'a', 'an', 'the', 'and', 'but', 'or', 'nor', 'for', 'so', 'yet',
    'as', 'at', 'by', 'in', 'of', 'off', 'on', 'per', 'to', 'up', 'via', 'vs',
}
# Se scriu asa cum sunt, nu se ating: acronime, unitati, marci.
INTACTE = {'VAT', 'IOR', 'EUR', 'TVA', 'sqm', 'Ilioara', 'Residence', 'Dristor', 'Titan'}

RX_CUVANT = re.compile(r"[A-Za-z][A-Za-z'’]*")

def cap_bucata(b):
    """Capitalizeaza o bucata alfabetica, pastrand restul cuvantului (ex: apostroful din what's)."""
    return b[0].upper() + b[1:]

def title_case(t):
    iesire = []
    poz = 0
    # taiem in jetoane pastrand separatorii, ca sa stim ce e primul/ultimul si ce vine dupa : sau |
    jetoane = re.split(r'(\s+)', t)
    indici_cuv = [i for i, j in enumerate(jetoane) if RX_CUVANT.search(j)]
    prim, ultim = (indici_cuv[0], indici_cuv[-1]) if indici_cuv else (-1, -1)
    dupa_semn = False
    for i, j in enumerate(jetoane):
        # Semnul se citeste de pe ORICE jeton, nu doar de pe unul cu litere. Altfel "2026:" nu
        # marcheaza inceput de clauza si iese "2026: a Buying Guide" in loc de "A Buying Guide".
        termina_clauza = j.rstrip().endswith((':', '|', '—'))
        if not RX_CUVANT.search(j):
            iesire.append(j)
            if j.strip():
                dupa_semn = termina_clauza
            continue
        gol = j
        if gol.strip() in INTACTE or (gol.upper() == gol and len(gol) > 1):
            iesire.append(gol)
            dupa_semn = termina_clauza
            continue
        # Bucatile alfabetice ale aceluiasi jeton: doar PRIMA poate fi fortata de pozitie. Restul
        # sunt parti de compus cu cratima si respecta lista de cuvinte mici, ca sa iasa
        # "Step-by-Step", nu "Step-By-Step", dar in acelasi timp "New-Build", fiindca "build" nu
        # e cuvant mic.
        contor = {'n': 0}
        def fix(m):
            c = m.group(0)
            contor['n'] += 1
            if c in INTACTE:
                return c
            prima = contor['n'] == 1
            forta = prima and ((i == prim) or (i == ultim) or dupa_semn)
            if not forta and c.lower() in MICI:
                return c.lower()
            return cap_bucata(c)
        iesire.append(RX_CUVANT.sub(fix, gol))
        dupa_semn = termina_clauza
    return ''.join(iesire)

def proceseaza(cale):
    html = open(cale, encoding='utf-8').read()
    m = re.search(r'<title>(.*?)</title>', html, re.S | re.I)
    if not m:
        return None
    v = re.sub(r'\s+', ' ', m.group(1)).strip()
    n = title_case(v)
    if n == v:
        return None
    if not DRY:
        h2 = html.replace(f'<title>{v}</title>', f'<title>{n}</title>', 1)
        for prop in ('og:title', 'twitter:title'):
            for q in ('"', "'"):
                for a in ('property', 'name'):
                    h2 = h2.replace(f'{a}={q}{prop}{q} content={q}{v}{q}',
                                    f'{a}={q}{prop}{q} content={q}{n}{q}')
                    h2 = h2.replace(f'content={q}{v}{q} {a}={q}{prop}{q}',
                                    f'content={q}{n}{q} {a}={q}{prop}{q}')
        open(cale, 'w', encoding='utf-8', newline='').write(h2)
    return (v, n)

baza = os.path.join(ROOT, 'en')
schimbate = []
for dp, dn, fn in os.walk(baza):
    dn[:] = [d for d in dn if d not in {'.git', '.engine', 'assets', 'fonts', 'film2'}]
    for f in fn:
        if f == 'index.html':
            r = proceseaza(os.path.join(dp, f))
            if r:
                schimbate.append((os.path.relpath(dp, baza).replace('\\', '/'), r))

print(f"{'[DRY] ' if DRY else ''}TITLURI EN ADUSE LA TITLE CASE: {len(schimbate)}\n")
for cale, (v, n) in schimbate:
    print(f"  {cale[:44]}")
    print(f"     inainte: {v}")
    print(f"     dupa   : {n}   ({len(n)} car.)")
peste = [(c, n) for c, (_, n) in schimbate if len(n) > 60]
print(f"\npeste 60 de caractere dupa schimbare: {len(peste)}")
