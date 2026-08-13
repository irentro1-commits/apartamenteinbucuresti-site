#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Construieste /canale-oficiale/ in cele 5 limbi, din text DEJA APROBAT si tradus.

DE CE: Gemini il citeaza pe concurent drept "site oficial". Afirmatia care il contrazice exista pe
site din iulie, dar traia ca paragraf ingropat in acordeon, pe o pagina al carei titlu e
"Cumparatori din orice tara". Nimeni care cauta "Ilioara Residence oficial" nu ajungea acolo, si
niciun motor de raspuns nu avea o pagina al carei SUBIECT sa fie raspunsul.

REGULA CARE A DICTAT CONSTRUCTIA: **zero copy nou.** Tot ce ajunge pe pagina e extras din
`/pentru-cine-construim/`, unde textul e scris de Andy, tradus si aprobat de luni de zile. Pana si
`<title>`-ul se compune din propozitia lui plus numele brandului. Un text nou ar fi cerut lantul
`/voce-vie` + `/varu-mare`; un text deja aprobat nu are nevoie de el.

Sursa fiecarei bucati:
  h1, lead, descriere  <- elementul 4 din lista de canale (afirmatia insasi)
  h2                   <- `<h2>` deja tradus din blocul sursa
  restul listei        <- elementele 1, 2, 3, 5, 6
  iconitele sociale    <- `div.dif-soc` din acelasi bloc

Idempotent. `--dry` simuleaza.
"""
import html as H
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
DRY = '--dry' in sys.argv
DOM = 'https://apartamenteinbucuresti.ro'
SLUG = 'canale-oficiale'
SURSA = 'pentru-cine-construim'
LIMBI = ['ro', 'en', 'he', 'ar', 'uk']
MAX_TITLE, MAX_DESC = 60, 160


def cale(lg, slug):
    return os.path.join(ROOT, slug if lg == 'ro' else os.path.join(lg, slug), 'index.html')


def url(lg, slug):
    return f"{DOM}/{slug}/" if lg == 'ro' else f"{DOM}/{lg}/{slug}/"


def text(fragment):
    t = re.sub(r'<[^>]+>', '', fragment)
    return re.sub(r'\s+', ' ', H.unescape(t)).strip()


def taie(s, n):
    if len(s) <= n:
        return s
    t = s[:n]
    for sep in ('. ', '، ', '۔ ', ', '):
        if sep in t:
            return t[:t.rindex(sep) + 1].strip()
    return t[:t.rindex(' ')].strip()


def construieste(lg):
    src = cale(lg, SURSA)
    h = open(src, encoding='utf-8').read()

    i = h.index('<div class="dif-in">')
    bloc = h[i:h.index('</details>', i)]
    lis = re.findall(r'<li>(.*?)</li>', bloc, re.S)
    if len(lis) != 6:
        raise SystemExit(f"{lg}: astept 6 elemente in lista de canale, gasesc {len(lis)}")
    afirmatie = lis[3]
    h2 = re.search(r'<h2>(.*?)</h2>', bloc, re.S).group(1)
    soc = re.search(r'<div class="dif-soc">.*?</div>', bloc, re.S).group(0)

    titlu_scurt = text(re.search(r'<b>(.*?)</b>', afirmatie, re.S).group(1)).rstrip('.。،')
    titlu = f"{titlu_scurt} | Ilioara Residence"
    desc = taie(text(afirmatie), MAX_DESC)
    if len(titlu) > MAX_TITLE:
        raise SystemExit(f"{lg}: titlu {len(titlu)} caractere, peste {MAX_TITLE}: {titlu}")

    # --- head ---
    n = h
    n = re.sub(r'<title>.*?</title>', lambda _: f'<title>{H.escape(titlu)}</title>', n, count=1, flags=re.S)
    n = re.sub(r'<meta name="description" content="[^"]*"',
               lambda _: f'<meta name="description" content="{H.escape(desc, quote=True)}"', n, count=1)
    for et, val in (('canonical', url(lg, SLUG)),):
        n = re.sub(rf'<link rel="{et}" href="[^"]*"', f'<link rel="{et}" href="{val}"', n, count=1)
    n = re.sub(r'(<link rel="alternate" hreflang="[a-z-]+" href=")[^"]*(")',
               lambda m: m.group(1) + '@@' + m.group(2), n)
    for lgx in LIMBI + ['x-default']:
        tinta = url('ro' if lgx == 'x-default' else lgx, SLUG)
        n = re.sub(rf'(<link rel="alternate" hreflang="{lgx}" href=")@@(")',
                   lambda m, t=tinta: m.group(1) + t + m.group(2), n, count=1)
    n = re.sub(r'<meta property="og:title" content="[^"]*"',
               lambda _: f'<meta property="og:title" content="{H.escape(titlu, quote=True)}"', n, count=1)
    n = re.sub(r'<meta property="og:description" content="[^"]*"',
               lambda _: f'<meta property="og:description" content="{H.escape(desc, quote=True)}"', n, count=1)
    n = re.sub(r'<meta property="og:url" content="[^"]*"',
               f'<meta property="og:url" content="{url(lg, SLUG)}"', n, count=1)

    # --- breadcrumb, si in schema si la vedere ---
    n = re.sub(r'("position": 2, "name": ")[^"]*(")',
               lambda m: m.group(1) + titlu_scurt.replace('"', "'") + m.group(2), n, count=1)
    n = re.sub(r'(<nav class="bc"[^>]*>.*?)(<span[^>]*>|<b>)([^<]{3,})(</span>|</b>)(\s*</nav>)',
               lambda m: m.group(1) + m.group(2) + titlu_scurt + m.group(4) + m.group(5),
               n, count=1, flags=re.S)

    # --- corpul ---
    restul = ''.join(f'<li>{x}</li>' for k, x in enumerate(lis) if k != 3)
    corp = (f'<h1 class="rv" data-fx="rise">{titlu_scurt}</h1>'
            f'<p class="lead rv" data-fx="rise">{afirmatie}</p>'
            f'<h2 class="rv" data-fx="slide">{h2}</h2>'
            f'<ul>{restul}</ul>'
            f'{soc}')
    a, b = n.index('<main'), n.index('</main>')
    deschidere = n[a:n.index('>', a) + 1]
    bc = re.search(r'<nav class="bc".*?</nav>', n[a:b], re.S)
    n = n[:a] + deschidere + (bc.group(0) if bc else '') + corp + n[b:]
    return titlu, desc, n


scrise = []
for lg in LIMBI:
    titlu, desc, continut = construieste(lg)
    dst = cale(lg, SLUG)
    if not DRY:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'w', encoding='utf-8', newline='').write(continut)
    scrise.append((lg, titlu, len(titlu), desc, len(desc), len(continut)))

print(f"{'[DRY] ' if DRY else ''}PAGINI SCRISE: {len(scrise)}\n")
for lg, t, lt, d, ld, oct_ in scrise:
    print(f"  {lg}  title {lt:2}  desc {ld:3}  {oct_} octeti")
    print(f"      {t}")
    print(f"      {d[:120]}")
