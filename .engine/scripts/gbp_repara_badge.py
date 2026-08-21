#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Repara markupul badge-ului montat de gbp_monteaza.py, ca sa foloseasca EXCLUSIV clasele
care exista deja in CSS. Fara clase noi = fara atingerea `assets/pagini-v34.css` = fara
bump de versiune (regula: /assets/* e immutable 1 an).

Doua corectii:
  1. homepage cinematic: `.ff-rev` stilizeaza `<a>`-ul DINAUNTRU (`.ff-rev a{...}`), nu ancora
     insasi. Deci wrapperul trebuie sa fie `<div class="ff-rev">` cu ancore FARA clasa.
     Montajul initial pusese `<div class="ff-act">` (clasa inexistenta) cu ancore `.ff-rev`.
  2. subpagini: a doua ancora avea `class="pf-rev pf-rev-w"`; `-w` nu exista in CSS.

Idempotent. Ruleaza cu --dry pentru simulare.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
DRY = '--dry' in sys.argv

def repara(html):
    # 1. wrapperul de homepage
    def fix_div(m):
        inner = m.group(1)
        inner = inner.replace('<a class="ff-rev ff-rev-w" ', '<a ')
        inner = inner.replace('<a class="ff-rev" ', '<a ')
        return '<div class="ff-rev">' + inner + '</div>'
    html = re.sub(r'<div class="ff-act">(.*?)</div>', fix_div, html, flags=re.S)
    # 2. clasa moarta de pe subpagini
    html = html.replace('class="pf-rev pf-rev-w"', 'class="pf-rev"')
    return html

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

print(f"{'[DRY] ' if DRY else ''}fisiere reparate: {n} din {len(fisiere)}")

# verificare: nicio clasa inexistenta ramasa
rest = 0
for f in fisiere:
    h = open(f, encoding='utf-8').read()
    if 'ff-act' in h or 'pf-rev-w' in h or 'ff-rev-w' in h:
        rest += 1
print(f"fisiere cu clase inexistente ramase: {rest}")
