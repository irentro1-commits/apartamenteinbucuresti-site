#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PASUL 2 din generare: blocul de diferentiere, sus in prima sectiune.

Vindem in mai multe locuri, proiectul nu are agent exclusiv, cifrele vin din documentatia
dezvoltatorului. Zero acuzatii nominale: doar fapte verificabile despre noi. Comutatorul e
<details> nativ, deci merge si daca scriptul cade.

DE CE E AICI, SI NU UN SCRIPT ONE-SHOT IN /tmp CA PANA ACUM (lectie platita 10 aug 2026):
blocul a fost injectat pe 4 aug direct in HTML, cu un script care a murit odata cu /tmp.
Sursa JSON n-a stiut niciodata de el. Prima regenerare a unui articol l-ar fi sters, tacut,
in cinci limbi. Orice pas care atinge HTML-ul generat traieste in pipeline, altfel pipeline-ul
minte: produce alt site decat cel care e live, si nimeni nu afla pana nu e prea tarziu.

Idempotent: sare peste paginile care au deja blocul.
"""
import argparse, glob, json, os, re, sys

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = json.load(open(os.path.join(ENGINE, "date", "dif.json"), encoding="utf-8"))

RETELE = [
    ("Instagram", "https://www.instagram.com/ilioara.residence/"),
    ("Facebook", "https://www.facebook.com/people/Ilioara-Residence/61573376259964/"),
    ("TikTok", "https://www.tiktok.com/@ilioara.residence"),
    ("LinkedIn", "https://www.linkedin.com/company/ilioara-residence/"),
    ("YouTube", "https://www.youtube.com/@ilioara.residence.bucharest"),
]

SCUT = ('<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M12 2.7l7.4 2.9v5.6c0 4.6-3.1 8.3-7.4 10.1-4.3-1.8-7.4-5.5-7.4-10.1V5.6z"/>'
        '<path d="M8.7 12.1l2.3 2.3 4.3-4.6"/></svg>')
TELEFON = ('<svg class="tic" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
           'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
           '<path d="M6.2 3.5h3.1l1.6 3.9-2 1.2a12.4 12.4 0 0 0 5.5 5.5l1.2-2 3.9 1.6v3.1'
           'a1.7 1.7 0 0 1-1.9 1.7C10.4 17.8 6.2 13.6 4.5 5.4A1.7 1.7 0 0 1 6.2 3.5z"/></svg>')
SAGEATA = ('<svg class="ch" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
           'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
           '<path d="M5 9l7 7 7-7"/></svg>')


def bloc(l, titlu_tag="h2"):
    """titlu_tag: pe paginile de articol titlul blocului e <h2>, ca sa nu rupa ierarhia
    h1 > h2 > h3 pe care o verifica gate-ul de STRUCTURA."""
    c = T[l]
    puncte = "".join(f"<li>{p}</li>" for p in c["puncte"])
    chip = "".join(f'<a href="{u}" target="_blank" rel="noopener">{n}</a>' for n, u in RETELE)
    return (
        f'\n<div class="dif rv" data-fx="rise">'
        f'<a class="dif-tel" href="tel:+40774096700">{TELEFON}'
        f'<span class="tw"><b>{c["tel"]}</b><span>{c["telSub"]}</span></span></a>'
        f'<details class="dif-d">'
        f'<summary>{SCUT}<span class="tx">{c["bara"]}'
        f'<span class="hn">{c["hint"]}</span></span>{SAGEATA}</summary>'
        f'<div class="dif-in"><{titlu_tag}>{c["titlu"]}</{titlu_tag}><ul>{puncte}</ul>'
        f'<div class="dif-soc">{chip}</div></div></details></div>\n')


def lang_of(h):
    m = re.search(r'<html[^>]*lang="([a-z]{2})"', h)
    return m.group(1) if m else "ro"


def injecteaza(h):
    """Intoarce (html, s_a_schimbat). Ancora: chiar inaintea primului <h2> sau al primului hero,
    deci blocul sta sub H1 / lead / byline pe orice tip de pagina, si nu taie firul lecturii."""
    if 'class="dif rv"' in h or "<main" not in h:
        return h, False
    l = lang_of(h)
    if l not in T:
        return h, False
    m0 = h.find("<main")
    zona = h[m0:m0 + 5000]
    poz = -1
    m = re.search(r'<(div class="hero|h2)', zona)
    if m:
        poz = m0 + m.start()
    else:
        for pat in [r'<p class="bdgp[^"]*"[^>]*>.*?</p>',
                    r'<p class="lead[^"]*"[^>]*>.*?</p>',
                    r'<div class="byline[^"]*"[^>]*>.*?</div>\s*</div>']:
            mm = re.search(pat, zona, re.S)
            if mm:
                poz = max(poz, m0 + mm.end())
    if poz <= 0:
        return h, False
    poz = scoate_din_ancora(h, m0, poz)
    return h[:poz] + bloc(l) + h[poz:], True


def scoate_din_ancora(h, m0, poz):
    """CAPCANA PLATITA PE 4 AUG 2026, si e singurul motiv pentru care exista functia asta.

    Pe indexul blogului primul <h2> din pagina e titlul din PRIMUL CARD, iar cardul intreg
    e o ancora. Ancorat acolo, blocul intra ANCORA IN ANCORA: HTML-ul nu permite asa ceva,
    deci parserul il repara singur si il muta afara. Ce vezi in DOM nu mai e ce ai scris in
    fisier, si asta a spart pagina de blog in cinci limbi. Verificarea trebuie facuta pe
    HTML-ul SERVIT, fiindca in DOM defectul e deja "reparat" si devine invizibil.

    Daca pozitia cade intr-o ancora deschisa, urcam inaintea containerului ei (<div class="grid">),
    nu doar inaintea ancorei: altfel blocul ar deveni o celula de grid.
    """
    seg = h[m0:poz]
    desch = [m.start() for m in re.finditer(r"<a\b", seg)]
    inch = [m.start() for m in re.finditer(r"</a>", seg)]
    if len(desch) <= len(inch):
        return poz
    p_ancora = m0 + desch[len(inch)]
    d = h.rfind("<div", m0, p_ancora)
    return d if d > m0 else p_ancora


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--doar", default="**/*.html",
                    help="tipar glob relativ la repo; implicit tot situl")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    pus = sarit = 0
    for fp in sorted(glob.glob(os.path.join(a.repo, a.doar), recursive=True)):
        h = open(fp, encoding="utf-8").read()
        h2, schimbat = injecteaza(h)
        if schimbat:
            pus += 1
            if a.apply:
                open(fp, "w", encoding="utf-8", newline="\n").write(h2)
        elif 'class="dif rv"' not in h and "<main" in h:
            sarit += 1
            print(f"  fara ancora: {os.path.relpath(fp, a.repo)}")
    print(f"pas_dif: {pus} blocuri puse, {sarit} pagini fara ancora  "
          f"({'APLICAT' if a.apply else 'PROBA'})")
