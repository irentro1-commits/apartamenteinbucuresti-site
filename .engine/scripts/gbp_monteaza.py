#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monteaza profilul Google Business pe site, din SURSA UNICA .engine/date/gbp.json.

Ce face, pe toate paginile si toate limbile:
  1. `sameAs` catre listarea Maps, `geo` si `hasMap` pe nodul ApartmentComplex si pe Organization
  2. `postalCode` in adresa, si corectia 032295 -> 032116
  3. legatura vizibila catre profil in footer (badge), fara NICIUN markup de rating pe ea

Ce NU face, deliberat: `aggregateRating`. Nici pe Organization (ineligibil, regula
self-serving), nici pe ApartmentComplex (tip nesuportat pentru review snippet).
`.engine/scripts/check_pages.py` pica buildul daca reapare. Vezi logul, 13 Aug 2026.

Idempotent: rulat de doua ori nu dubleaza nimic. Ruleaza cu --dry ca sa vezi ce ar face.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
GBP = json.load(open(os.path.join(ROOT, '.engine', 'date', 'gbp.json'), encoding='utf-8'))

DRY = '--dry' in sys.argv
MAPS, REVIEW = GBP['mapsUrl'], GBP['reviewUrl']
LAT, LNG = GBP['geo']['lat'], GBP['geo']['lng']
ADR = GBP['adresa']
RATING, NREV = GBP['rating'], GBP['reviewCount']

GEO = {"@type": "GeoCoordinates", "latitude": LAT, "longitude": LNG}

# Textul badge-ului, per limba. E TEXT VIZIBIL, nu date structurate: nicio politica
# de rich result nu se aplica pe el, si se verifica cu un click.
BADGE = {
    'ro': (f'{RATING} pe Google', f'{NREV} recenzii', 'Lasă-ne o părere'),
    'en': (f'{GBP["ratingPunct"]} on Google', f'{NREV} reviews', 'Leave us a review'),
    'uk': (f'{GBP["ratingPunct"]} на Google', f'{NREV} відгуки', 'Залиште відгук'),
    'he': (f'{GBP["ratingPunct"]} בגוגל', f'{NREV} ביקורות', 'כתבו לנו ביקורת'),
    'ar': (f'{GBP["ratingPunct"]} على جوجل', f'{NREV} تقييمات', 'اتركوا لنا تقييماً'),
}

def limba(path, html):
    m = re.search(r'<html[^>]*lang="([a-z]{2})"', html)
    return m.group(1) if m else 'ro'

def badge_html(lg, cls):
    nota, nr, cta = BADGE.get(lg, BADGE['ro'])
    return (f'<a class="{cls}" href="{MAPS}" target="_blank" rel="noopener">'
            f'<span class="st">★</span> <b>{nota}</b> · {nr}</a>'
            f'<a class="{cls} {cls}-w" href="{REVIEW}" target="_blank" rel="noopener">{cta}</a>')

def pune_in_nod(nod):
    """sameAs + geo + hasMap + postalCode pe un nod de entitate. Intoarce True daca a schimbat ceva."""
    schimbat = False
    same = nod.get('sameAs')
    same = [same] if isinstance(same, str) else (same or [])
    if not any('maps' in s and 'google' in s for s in same):
        same = [s for s in same if 'google.com/maps' not in s]  # scoate orice listare veche
        nod['sameAs'] = same + [MAPS]
        schimbat = True
    elif MAPS not in same:
        nod['sameAs'] = [s for s in same if 'google.com/maps' not in s] + [MAPS]
        schimbat = True
    if nod.get('geo') != GEO:
        nod['geo'] = GEO; schimbat = True
    if nod.get('hasMap') != MAPS:
        nod['hasMap'] = MAPS; schimbat = True
    ad = nod.get('address')
    if isinstance(ad, dict):
        if ad.get('postalCode') != ADR['postalCode']:
            ad['postalCode'] = ADR['postalCode']; schimbat = True
        if ad.get('streetAddress') != ADR['streetAddress']:
            ad['streetAddress'] = ADR['streetAddress']; schimbat = True
    if 'aggregateRating' in nod:
        del nod['aggregateRating']; schimbat = True
    return schimbat

TINTE = ('ApartmentComplex', 'Organization')

def proceseaza(path):
    html = open(path, encoding='utf-8').read()
    orig = html
    lg = limba(path, html)
    n_sch = 0

    for bloc in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            date = json.loads(bloc)
        except Exception:
            continue
        items = date if isinstance(date, list) else [date]
        atins = False
        for it in items:
            if not isinstance(it, dict):
                continue
            t = it.get('@type')
            t = t if isinstance(t, list) else [t]
            if any(x in TINTE for x in t):
                atins |= pune_in_nod(it)
        if atins:
            spatiat = '": "' in bloc or '", "' in bloc
            sep = (', ', ': ') if spatiat else (',', ':')
            nou = json.dumps(date, ensure_ascii=False, separators=sep)
            html = html.replace(bloc, nou, 1)
            n_sch += 1

    # cod postal gresit oriunde in pagina (homepage-urile aveau 032295)
    if '032295' in html:
        html = html.replace('032295', ADR['postalCode'])

    # badge vizibil: subpagini (.pf-act) si homepage cinematic (dupa .ff-desc)
    n_badge = 0
    if 'class="pf-rev"' not in html and '<div class="pf-act">' in html:
        html = html.replace('<div class="pf-act">', '<div class="pf-act">' + badge_html(lg, 'pf-rev'), 1)
        n_badge = 1
    elif 'class="ff-rev"' not in html:
        m = re.search(r'(<p class="ff-desc">.*?</p>)', html, re.S)
        if m:
            html = html.replace(m.group(1), m.group(1) + '<div class="ff-act">' + badge_html(lg, 'ff-rev') + '</div>', 1)
            n_badge = 1

    if html != orig and not DRY:
        open(path, 'w', encoding='utf-8', newline='').write(html)
    return (html != orig), n_sch, n_badge

sari = {'.git', '.github', '.engine', 'assets', 'fonts', 'film2', 'node_modules'}
fisiere = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in sari]
    for f in filenames:
        if f.endswith('.html'):
            fisiere.append(os.path.join(dirpath, f))

tot = sch = bdg = 0
for f in sorted(fisiere):
    ok, n_sch, n_b = proceseaza(f)
    tot += ok; sch += n_sch; bdg += n_b

print(f"{'[DRY] ' if DRY else ''}fisiere HTML scanate : {len(fisiere)}")
print(f"{'[DRY] ' if DRY else ''}fisiere modificate   : {tot}")
print(f"{'[DRY] ' if DRY else ''}blocuri JSON-LD atinse: {sch}")
print(f"{'[DRY] ' if DRY else ''}badge-uri montate    : {bdg}")
