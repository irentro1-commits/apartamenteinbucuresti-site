#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pune butonul de WhatsApp INAPOI pe primul loc in `.pf-act`.

Montajul initial a injectat cele doua legaturi Google la inceputul containerului, ceea ce
a impins CTA-ul principal pe locul trei. WhatsApp e canalul prin care vin cererile; el
ramane primul, iar dovada sociala vine dupa el.

Idempotent: daca `.pf-wa` e deja primul, nu atinge nimic.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
DRY = '--dry' in sys.argv

# <a class="pf-rev" ...>...</a> repetat, urmat imediat de <a class="pf-wa" ...>...</a>
TIPAR = re.compile(
    r'(<div class="pf-act">)'
    r'((?:<a class="pf-rev"[^>]*>.*?</a>)+)'
    r'(\s*)'
    r'(<a class="pf-wa"[^>]*>.*?</a>)',
    re.S)

def repara(html):
    # devine: <div class="pf-act">  <a pf-wa>...</a>  <a pf-rev>...</a><a pf-rev>...</a>
    return TIPAR.sub(lambda m: m.group(1) + m.group(3) + m.group(4) + m.group(3) + m.group(2), html)

sari = {'.git', '.github', '.engine', 'assets', 'fonts', 'film2', 'node_modules'}
fisiere = []
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in sari]
    fisiere += [os.path.join(dp, f) for f in fn if f.endswith('.html')]

n = 0
for f in sorted(fisiere):
    h = open(f, encoding='utf-8').read()
    nou = repara(h)
    if nou != h:
        n += 1
        if not DRY:
            open(f, 'w', encoding='utf-8', newline='').write(nou)

print(f"{'[DRY] ' if DRY else ''}fisiere cu ordinea corectata: {n} din {len(fisiere)}")

gresite = sum(1 for f in fisiere
              if re.search(r'<div class="pf-act"><a class="pf-rev"', open(f, encoding='utf-8').read()))
print(f"fisiere in care WhatsApp NU e primul: {gresite}")
