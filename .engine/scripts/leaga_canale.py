#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Leaga /canale-oficiale/ de restul sitului: sitemap, footer pe toate paginile, meniul homepage-ului.

O pagina orfana nu se indexeaza, oricat de bine ar fi scrisa. Si aici anchor textul CHIAR conteaza:
legatura poarta exact propozitia pe care vrem sa o invete motoarele, nu un "afla mai multe".

Ancora de insertie e legatura catre `/pentru-cine-construim/`, care exista in footerul fiecarei
pagini din toate cele 5 limbi, cu acelasi tipar de href. Nu depind de `aria-label`, care e tradus.

Idempotent. `--dry` simuleaza.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
DRY = '--dry' in sys.argv
DOM = 'https://apartamenteinbucuresti.ro'
LIMBI = ['ro', 'en', 'he', 'ar', 'uk']
AZI = '2026-08-14'


def url(lg):
    return f"{DOM}/canale-oficiale/" if lg == 'ro' else f"{DOM}/{lg}/canale-oficiale/"


def cale_rel(lg):
    return "/canale-oficiale/" if lg == 'ro' else f"/{lg}/canale-oficiale/"


# eticheta legaturii = chiar h1-ul paginii, adica propozitia aprobata. Zero copy nou.
ETICHETA = {}
for lg in LIMBI:
    p = os.path.join(ROOT, 'canale-oficiale' if lg == 'ro' else os.path.join(lg, 'canale-oficiale'),
                     'index.html')
    h = open(p, encoding='utf-8').read()
    ETICHETA[lg] = re.sub(r'<[^>]+>', '', re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S).group(1)).strip()

# ------------------------------------------------------------------ 1. sitemap
sm_p = os.path.join(ROOT, 'sitemap.xml')
sm = open(sm_p, encoding='utf-8').read()
if 'canale-oficiale' not in sm:
    alt = ''.join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{url(l)}"/>' for l in LIMBI)
    alt += f'<xhtml:link rel="alternate" hreflang="x-default" href="{url("ro")}"/>'
    intrari = ''.join(f'<url><loc>{url(l)}</loc><lastmod>{AZI}</lastmod>{alt}</url>\n' for l in LIMBI)
    sm = sm.replace('</urlset>', intrari + '</urlset>')
    if not DRY:
        open(sm_p, 'w', encoding='utf-8', newline='').write(sm)
    print(f"sitemap: {len(LIMBI)} URL adaugate")
else:
    print("sitemap: deja prezent")

# ------------------------------------------------------ 2. footer + meniu homepage
sari = {'.git', '.github', '.engine', 'assets', 'fonts', 'film2', 'node_modules'}
fisiere = []
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in sari]
    fisiere += [os.path.join(dp, f) for f in fn if f.endswith('.html')]

n_footer = n_meniu = 0
for f in sorted(fisiere):
    h = open(f, encoding='utf-8').read()
    if 'canale-oficiale' in h:
        continue
    m = re.search(r'<html[^>]*lang="([a-z]{2})"', h)
    lg = m.group(1) if m else 'ro'
    if lg not in LIMBI:
        continue
    tinta, eticheta = cale_rel(lg), ETICHETA[lg]
    ancora = f'/pentru-cine-construim/' if lg == 'ro' else f'/{lg}/pentru-cine-construim/'
    nou = h

    # footerul paginilor obisnuite
    tipar = re.compile(rf'(<a href="{re.escape(ancora)}"[^>]*>.*?</a>)', re.S)
    if tipar.search(nou):
        nou = tipar.sub(lambda mm: mm.group(1) + f'\n      <a href="{tinta}">{eticheta}</a>',
                        nou, count=1)
        n_footer += 1
    # meniul footerului cinematic de pe homepage
    elif '<nav class="ff-nav"' in nou:
        nou = nou.replace('<nav class="ff-nav" aria-label',
                          f'<nav class="ff-nav" data-x aria-label', 1)
        nou = re.sub(r'(<nav class="ff-nav" data-x[^>]*>)',
                     lambda mm: mm.group(1) + f'<a href="{tinta}">{eticheta}</a>', nou, count=1)
        nou = nou.replace(' data-x', '', 1)
        n_meniu += 1
    else:
        continue

    if not DRY:
        open(f, 'w', encoding='utf-8', newline='').write(nou)

print(f"{'[DRY] ' if DRY else ''}legatura in footer: {n_footer} pagini")
print(f"{'[DRY] ' if DRY else ''}legatura in meniul homepage: {n_meniu} pagini")
for lg in LIMBI:
    print(f"   {lg}: {ETICHETA[lg]}")
