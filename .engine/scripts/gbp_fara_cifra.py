#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scoate nota si numarul de recenzii din legatura vizibila. Ramane doar trimiterea la profil.

Decizia lui Andy, 13 Aug 2026: *"scoate cifra si lasa doar recenziile"*. Motivul e practic:
o cifra scrisa in pagina se invecheste exact cand incepe sa creasca, iar reimprospatarea
automata ar fi cerut cheie Places API cu facturare. Fara cifra, pagina nu are ce sa
imbatraneasca, iar semnalul care conteaza (legatura site-profil) ramane intreg.

Nota si numarul raman MASURATE in `.engine/date/gbp.json`, ca fapt, dar nu se mai randeaza.

Idempotent. `--dry` pentru simulare.
"""
import os, re, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
GBP = json.load(open(os.path.join(ROOT, '.engine', 'date', 'gbp.json'), encoding='utf-8'))
DRY = '--dry' in sys.argv
MAPS = GBP['mapsUrl']

TEXT = {
    'ro': 'Vezi recenziile pe Google',
    'en': 'See our Google reviews',
    'uk': 'Відгуки на Google',
    'he': 'ביקורות בגוגל',
    'ar': 'تقييماتنا على جوجل',
}

def limba(html):
    m = re.search(r'<html[^>]*lang="([a-z]{2})"', html)
    return m.group(1) if m else 'ro'

def repara(html):
    lg = limba(html)
    nou = f'<span class="st">★</span> {TEXT.get(lg, TEXT["ro"])}'
    # ancora catre listare: ii inlocuim DOAR continutul, nu atributele
    tipar = re.compile(r'(<a(?:\s+class="[^"]*")?\s+href="' + re.escape(MAPS) + r'"[^>]*>)(.*?)(</a>)', re.S)
    return tipar.sub(lambda m: m.group(1) + nou + m.group(3), html)

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

print(f"{'[DRY] ' if DRY else ''}fisiere cu cifra scoasa: {n} din {len(fisiere)}")

# verificare: nicio nota si niciun numar de recenzii ramase in pagini
rest = []
for f in fisiere:
    h = open(f, encoding='utf-8').read()
    if re.search(r'(5,0|5\.0)\s*(pe Google|on Google|на Google|בגוגל|على جوجل)', h) or re.search(r'\d+\s*recenzii', h):
        rest.append(f)
print(f"pagini cu nota sau numar ramase: {len(rest)}  {rest[:3]}")
