#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scoate legatura catre /canale-oficiale/ din MENIUL numerotat si o pune in FOOTER, unde e locul ei.

Ce am gresit: am injectat `<a href>text</a>`, forma corecta pentru footer, la PRIMA aparitie a
ancorei de referinta. Prima aparitie e insa in `nav.mn-list`, meniul complet, unde fiecare element
are alta structura:

    <a href="..." style="--d:300ms"><span class="no">07</span><span class="nm">Titlu</span><em class="hint">nota</em></a>

Ancora mea, fara `no`, fara `nm` si fara `hint`, a randat ca link brut albastru intre elementele
07 si 08. Andy, imediat: *"ba ce plm e cu meniu lasta wtf"*.

De ce NU o fac element de meniu in regula: ar cere renumerotarea a trei elemente si decalarea
delayurilor de animatie, adica o schimbare de design pe un meniu gandit, pentru o pagina de nisa.
Footerul o poarta la fel de bine, e tot sitewide, si acolo forma `<a href>text</a>` e cea nativa.

LECTIA, si e generala: cand injectezi intr-o navigatie, structura elementului vecin e contractul.
Se copiaza tiparul vecinului, nu doar href-ul si textul. Iar ancora de insertie se alege dupa
CONTAINER, nu dupa prima potrivire din document.

Idempotent. `--dry` simuleaza.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
DRY = '--dry' in sys.argv

RX_LEG = re.compile(r'\s*<a href="(/(?:[a-z]{2}/)?canale-oficiale/)">([^<]*)</a>')


def bloc(html, clasa):
    m = re.search(rf'<nav class="{clasa}"[^>]*>.*?</nav>', html, re.S)
    return m


def coloana_despre(html):
    """Coloana de footer care tine legaturile 'despre', gasita dupa CONTINUT, nu dupa `aria-label`.

    `aria-label` e tradus in fiecare limba, deci cautarea dupa el gaseste doar paginile romanesti:
    prima varianta a scriptului punea legatura pe 37 de pagini din 186 si o pierdea pe restul.
    Coloana asta e, in orice limba, cea care contine legatura catre `pentru-cine-construim`.
    """
    for m in re.finditer(r'<nav class="pf-col"[^>]*>.*?</nav>', html, re.S):
        if 'pentru-cine-construim/' in m.group(0):
            return m
    return None


scos = pus_pf = pus_ff = 0
sari = {'.git', '.github', '.engine', 'assets', 'fonts', 'film2', 'node_modules'}
fisiere = []
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in sari]
    fisiere += [os.path.join(dp, f) for f in fn if f.endswith('.html')]

for f in sorted(fisiere):
    h = open(f, encoding='utf-8').read()
    orig = h

    # 1. scoate din meniul numerotat
    mn = bloc(h, 'mn-list')
    if mn and 'canale-oficiale' in mn.group(0):
        m = RX_LEG.search(mn.group(0))
        if m:
            tinta, eticheta = m.group(1), m.group(2)
            h = h.replace(mn.group(0), RX_LEG.sub('', mn.group(0), count=1), 1)
            scos += 1
        else:
            tinta = eticheta = None
    else:
        m2 = RX_LEG.search(h)
        tinta, eticheta = (m2.group(1), m2.group(2)) if m2 else (None, None)

    # 2. pune in footer, daca nu e deja acolo
    if tinta:
        pf = coloana_despre(h)
        if pf and 'canale-oficiale' not in pf.group(0):
            nou = pf.group(0).replace('</nav>', f'<a href="{tinta}">{eticheta}</a>\n    </nav>', 1)
            h = h.replace(pf.group(0), nou, 1)
            pus_pf += 1
        elif not pf:
            ff = bloc(h, 'ff-nav')
            if ff and 'canale-oficiale' not in ff.group(0):
                nou = ff.group(0).replace('</nav>', f'<a href="{tinta}">{eticheta}</a></nav>', 1)
                h = h.replace(ff.group(0), nou, 1)
                pus_ff += 1

    if h != orig and not DRY:
        open(f, 'w', encoding='utf-8', newline='').write(h)

print(f"{'[DRY] ' if DRY else ''}scos din meniul numerotat : {scos}")
print(f"{'[DRY] ' if DRY else ''}pus in footerul paginilor : {pus_pf}")
print(f"{'[DRY] ' if DRY else ''}pus in footerul cinematic : {pus_ff}")

ramase = sum(1 for f in fisiere
             if (b := bloc(open(f, encoding='utf-8').read(), 'mn-list')) and 'canale-oficiale' in b.group(0))
print(f"pagini cu legatura RAMASA in meniul numerotat: {ramase}")
