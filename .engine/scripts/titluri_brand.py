#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Duce brandul in <title> pe paginile care il pot purta, fara sa treaca de pragul de FAIL.

DE CE: Florin detine `ilioararesidence.ro` si are "Ilioara Residence" in titlu pe 9 din 9 pagini
principale. Noi aveam brandul pe 8 din 38 de pagini RO, si pe 0 din 12 pagini de apartament.
Andy, 13 Aug 2026: *"TREBYUIE SA IL FUTEM RAU AICI SI SA MAI CREAM NISTE PAGINI NOI ... SA AVEM
MA IMULTE PAGINI CU LIAORA RESIDENCE IN METE TILU"*.

PRAGURI, din `master-website/assets/praguri.json` (sursa unica): FAIL peste 60 de caractere,
banda buna 50-55. Titlurile de apartament erau deja la 49-52, deci brandul NU se poate lipi la
coada: pretul si TVA-ul ies din titlu (raman in descriere si pe pagina) si intra etajul, care
ajuta si omul sa distinga intre suprafete apropiate.

Regula de siguranta: daca varianta cu etaj trece de 60, se cade pe varianta fara etaj. Nicio
pagina nu iese peste prag, si scriptul o spune daca s-ar intampla.

CE NU ATINGE: cei 3 piloni generici (`apartamente-noi-bucuresti`, `blocuri-noi-bucuresti`,
`apartamente-blocuri-noi-bucuresti`). Aia vaneaza cautare generica, nu de brand; brandul acolo
strica potrivirea. Decizia lui Andy: *"de acum incolo fortam cu blogurile pe apartamente noi si
blocuri noi"*.

Idempotent. `--dry` simuleaza.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
DRY = '--dry' in sys.argv
BRAND = 'Ilioara Residence'
SUFIX = f' | {BRAND}'
PRAG_FAIL = 60

# pretul + TVA la coada titlului, in toate cele 5 limbi (virgula araba inclusa)
RX_PRET = re.compile(r'[,،]\s*[\d.٫٬]+\s*EUR\s*\+\s*TVA\s*21%\s*$', re.I)

ETAJ = {
    'ro': (', etaj {n}', ', parter'),
    'en': (', Floor {n}', ', Ground Floor'),
    'uk': (', поверх {n}', ', перший поверх'),
    'he': (', קומה {n}', ', קומת קרקע'),
    'ar': ('، الطابق {n}', '، الطابق الأرضي'),
}

def limba(html):
    m = re.search(r'<html[^>]*lang="([a-z]{2})"', html)
    return m.group(1) if m else 'ro'

def titlu(html):
    m = re.search(r'<title>(.*?)</title>', html, re.S | re.I)
    return re.sub(r'\s+', ' ', m.group(1)).strip() if m else None

def pune_titlu(html, vechi, nou):
    """Schimba <title> si, daca exista, og:title / twitter:title care il oglindesc."""
    html = html.replace(f'<title>{vechi}</title>', f'<title>{nou}</title>', 1)
    for prop in ('og:title', 'twitter:title'):
        for q in ('"', "'"):
            html = html.replace(f'property={q}{prop}{q} content={q}{vechi}{q}',
                                f'property={q}{prop}{q} content={q}{nou}{q}')
            html = html.replace(f'name={q}{prop}{q} content={q}{vechi}{q}',
                                f'name={q}{prop}{q} content={q}{nou}{q}')
            html = html.replace(f'content={q}{vechi}{q} property={q}{prop}{q}',
                                f'content={q}{nou}{q} property={q}{prop}{q}')
            html = html.replace(f'content={q}{vechi}{q} name={q}{prop}{q}',
                                f'content={q}{nou}{q} name={q}{prop}{q}')
    return html

def etaj_din_slug(slug, lg):
    cu_n, parter = ETAJ[lg]
    if 'parter' in slug:
        return parter
    m = re.search(r'etaj-(\d+)', slug)
    return cu_n.format(n=m.group(1)) if m else ''

def nou_apartament(vechi, slug, lg):
    baza = RX_PRET.sub('', vechi).rstrip(' ,،')
    cu_etaj = baza + etaj_din_slug(slug, lg) + SUFIX
    if len(cu_etaj) <= PRAG_FAIL:
        return cu_etaj
    fara = baza + SUFIX
    return fara if len(fara) <= PRAG_FAIL else None

# paginile principale care primesc brandul la coada, daca incap
PRINCIPALE = ('apartamente', 'preturi', 'dotari', 'zona', 'parcare')

def proceseaza(cale, slug, tip):
    html = open(cale, encoding='utf-8').read()
    v = titlu(html)
    if not v or BRAND in v:
        return None
    lg = limba(html)
    n = nou_apartament(v, slug, lg) if tip == 'apt' else (
        v + SUFIX if len(v + SUFIX) <= PRAG_FAIL else None)
    if not n or n == v:
        return ('PESTE-PRAG', v, len(v), None, None)
    if not DRY:
        open(cale, 'w', encoding='utf-8', newline='').write(pune_titlu(html, v, n))
    return ('OK', v, len(v), n, len(n))

randuri, peste = [], []
for lg_dir in ['', 'en/', 'he/', 'ar/', 'uk/']:
    baza = os.path.join(ROOT, lg_dir.strip('/')) if lg_dir else ROOT
    d_apt = os.path.join(baza, 'apartamente')
    if os.path.isdir(d_apt):
        for slug in sorted(os.listdir(d_apt)):
            f = os.path.join(d_apt, slug, 'index.html')
            if os.path.isfile(f):
                r = proceseaza(f, slug, 'apt')
                if r:
                    (peste if r[0] == 'PESTE-PRAG' else randuri).append((lg_dir or 'ro', slug, r))
    for pag in PRINCIPALE:
        f = os.path.join(baza, pag, 'index.html')
        if os.path.isfile(f):
            r = proceseaza(f, pag, 'pag')
            if r:
                (peste if r[0] == 'PESTE-PRAG' else randuri).append((lg_dir or 'ro', pag, r))

print(f"{'[DRY] ' if DRY else ''}TITLURI SCHIMBATE: {len(randuri)}\n")
for lg, slug, (_, v, lv, n, ln) in randuri:
    print(f"  {lg:3} {slug[:40]:40} {lv:3}->{ln:3}  {n}")
if peste:
    print(f"\nNU AU INCAPUT SUB {PRAG_FAIL} (raman neatinse, cer scurtare de mana): {len(peste)}")
    for lg, slug, (_, v, lv, _, _) in peste:
        print(f"  {lg:3} {slug[:40]:40} {lv:3}  {v}")
lungimi = [ln for _, _, (_, _, _, _, ln) in randuri]
if lungimi:
    print(f"\nlungimi noi: min {min(lungimi)}, max {max(lungimi)}, peste {PRAG_FAIL}: "
          f"{sum(1 for x in lungimi if x > PRAG_FAIL)}")
