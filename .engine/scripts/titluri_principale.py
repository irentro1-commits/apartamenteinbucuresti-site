#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Duce brandul in <title> pe cele 5 pagini principale, in toate limbile, taind clauza finala
cand nu incape.

De ce e nevoie de un al doilea pas: pe paginile de apartament brandul a intrat dupa ce a iesit
pretul din titlu. Aici titlurile sunt deja lungi din alt motiv, si patru din ele (`/parcare/` in
ro, en, ar, uk) erau DEJA peste pragul de FAIL inainte de orice atingere de-a noastra: 67, 68,
78 si 69 de caractere. Un titlu de 78 e trunchiat oricum in SERP, deci clauza de pret nu se
pierde, se muta acolo unde era deja citita: descrierea si pagina.

METODA, si e deliberat mecanica: se taie ULTIMA clauza (dupa ultimul `:` sau ultima virgula,
inclusiv cea araba `،`), nu se scrie copy nou. Cuvintele raman ale traducatorului. Se taie doar
cat trebuie ca sa incapa brandul sub 60, clauza cu clauza, si daca tot nu incape se lasa pagina
neatinsa si scriptul o spune.

Idempotent. `--dry` simuleaza.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
DRY = '--dry' in sys.argv
BRAND = 'Ilioara Residence'
SUFIX = f' | {BRAND}'
PRAG = 60
PAGINI = ('apartamente', 'preturi', 'dotari', 'zona', 'parcare')
TAIETURI = re.compile(r'^(.*?)\s*[:,،]\s*[^:,،]+$', re.S)
# Parantezele pleaca INAINTEA clauzelor. Motiv masurat pe he/preturi si ar/preturi: taierea pe
# clauze scotea orasul ("בוקרשט", "بوخارست") si pastra paranteza cu numele cartierului, adica
# exact pe dos fata de ce cauta un cumparator din afara. Cartierul e context, orasul e cuvantul-cheie.
RX_PAREN = re.compile(r'\s*\([^()]*\)')

def taie(t):
    if RX_PAREN.search(t):
        return RX_PAREN.sub('', t).strip().strip(':,،').strip()
    m = TAIETURI.match(t)
    return m.group(1).strip() if m else None

def proceseaza(cale):
    html = open(cale, encoding='utf-8').read()
    m = re.search(r'<title>(.*?)</title>', html, re.S | re.I)
    if not m:
        return None
    v = re.sub(r'\s+', ' ', m.group(1)).strip()
    if BRAND in v:
        return ('DEJA', v, len(v), v, len(v))
    baza = v
    while len(baza + SUFIX) > PRAG:
        scurt = taie(baza)
        if not scurt or scurt == baza:
            return ('NU-INCAPE', v, len(v), None, None)
        baza = scurt
    n = baza + SUFIX
    if not DRY:
        html2 = html.replace(f'<title>{v}</title>', f'<title>{n}</title>', 1)
        for prop in ('og:title', 'twitter:title'):
            for q in ('"', "'"):
                for a in ('property', 'name'):
                    html2 = html2.replace(f'{a}={q}{prop}{q} content={q}{v}{q}',
                                          f'{a}={q}{prop}{q} content={q}{n}{q}')
                    html2 = html2.replace(f'content={q}{v}{q} {a}={q}{prop}{q}',
                                          f'content={q}{n}{q} {a}={q}{prop}{q}')
        open(cale, 'w', encoding='utf-8', newline='').write(html2)
    return ('OK', v, len(v), n, len(n))

schimbate, deja, blocate = [], 0, []
for lg in ['', 'en', 'he', 'ar', 'uk']:
    baza = os.path.join(ROOT, lg) if lg else ROOT
    for pag in PAGINI:
        f = os.path.join(baza, pag, 'index.html')
        if not os.path.isfile(f):
            continue
        r = proceseaza(f)
        if not r:
            continue
        if r[0] == 'DEJA':
            deja += 1
        elif r[0] == 'NU-INCAPE':
            blocate.append((lg or 'ro', pag, r))
        else:
            schimbate.append((lg or 'ro', pag, r))

print(f"{'[DRY] ' if DRY else ''}SCHIMBATE: {len(schimbate)} | aveau deja brandul: {deja} | blocate: {len(blocate)}\n")
for lg, pag, (_, v, lv, n, ln) in schimbate:
    print(f"  {lg:3} {pag:12} {lv:3}->{ln:3}")
    print(f"      inainte: {v}")
    print(f"      dupa   : {n}")
for lg, pag, (_, v, lv, _, _) in blocate:
    print(f"  BLOCAT {lg:3} {pag:12} {lv:3}  {v}")
