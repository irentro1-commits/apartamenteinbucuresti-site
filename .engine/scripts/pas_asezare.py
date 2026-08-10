#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PASUL 3 din generare: asezarea textului in pagina, cu spatii nedespartitoare.

Doua legaturi, si fac lucruri diferite:

1. ULTIMELE DOUA cuvinte ale fiecarui bloc. Un cuvant nu mai ramane singur pe ultimul rand
   nici in browserele care inca nu au `text-wrap: pretty`.
2. PRIMELE DOUA cuvinte ale fiecarei fraze noi. Asa o propozitie nu mai poate porni cu un
   singur cuvant lipit de capatul randului: daca nu incap amandoua, trec amandoua pe randul
   urmator. Asta e defectul reclamat de Andy: "SCRISUL IN PAGINA CITIBIL SI NU ORFAN".

CSS-ul de asezare (text-wrap: balance/pretty + masura in em) traieste in `assets/pagini-vNN.css`
si nu se atinge de aici. Aici se face DOAR legarea, pe HTML-ul deja generat.

DE CE E AICI (lectie platita 10 aug 2026): legarile s-au facut pe 4 aug cu un script one-shot
din /tmp, direct pe HTML. Sursa JSON n-a stiut de ele. O regenerare din JSON scadea de la
93 la 2 spatii nedespartitoare pe pagina, adica intorcea gate-ul de ASEZARE din PASS in FAIL,
in cinci limbi deodata, fara ca nimic sa semnaleze.

Idempotent: legatura care exista deja nu se dubleaza (se verifica NBSP in spatiul respectiv).
"""
import argparse, glob, os, re, sys

NB = " "

# blocurile de proza in care se leaga cuvintele
TAGURI = r"(?:p|li|figcaption|blockquote|dd|dt|h1|h2|h3|h4)"
# sfarsit de fraza: punct, semn de intrebare sau de exclamare, urmat de spatiu si majuscula
FRAZA = re.compile(r"(?<=[a-zăâîșțA-ZĂÂÎȘȚ0-9\)\"”])([.!?…])\s+(?=[A-ZĂÂÎȘȚ])")


def leaga_final(t):
    """Ultimele doua cuvinte ale blocului, lipite. Nu atinge textul din interiorul etichetelor."""
    bucati = re.split(r"(<[^>]+>)", t)
    for i in range(len(bucati) - 1, -1, -1):
        s = bucati[i]
        if s.startswith("<") or not s.strip():
            continue
        m = re.match(r"^(.*?)(\S+)(\s+)(\S+)(\s*)$", s, re.S)
        if m and NB not in m.group(3):
            bucati[i] = m.group(1) + m.group(2) + NB + m.group(4) + m.group(5)
        break
    return "".join(bucati)


def leaga_fraze(t):
    """Primele doua cuvinte ale fiecarei fraze noi, lipite.
    Sarim potrivirile care cad INAINTE de pozitia deja consumata: doua sfarsituri de fraza
    apropiate ("... jos. Atat. In alta parte") produceau altfel dublarea cuvantului,
    fiindca a doua potrivire era gasita pe textul original, nu pe cel deja rescris."""
    bucati = re.split(r"(<[^>]+>)", t)
    for i, s in enumerate(bucati):
        if s.startswith("<") or not s.strip():
            continue
        # cazul "</b>. Il arata": punctul deschide fragmentul, deci privirea inapoi a
        # tiparului nu are pe ce sa cada. Il tratam separat, la inceput de fragment.
        mi = re.match(r"^([.!?…])(\s+)(\S+)(\s+)(\S+)", s)
        if mi and NB not in mi.group(4):
            s = mi.group(1) + mi.group(2) + mi.group(3) + NB + mi.group(5) + s[mi.end():]
        out, poz = [], 0
        for m in FRAZA.finditer(s):
            if m.start() < poz:          # deja consumat de potrivirea anterioara
                continue
            out.append(s[poz:m.end()])
            rest = s[m.end():]
            mm = re.match(r"^(\S+)(\s+)(\S+)", rest)
            if mm and NB not in mm.group(2):
                out.append(mm.group(1) + NB + mm.group(3))
                poz = m.end() + mm.end()
            else:
                poz = m.end()
        out.append(s[poz:])
        bucati[i] = "".join(out)
    return "".join(bucati)


BLOC = re.compile(r"(<(" + TAGURI + r")\b[^>]*>)(.*?)(</\2>)", re.S | re.I)


def rescrie(h):
    n = [0, 0]

    def per(m):
        cap, tag, corp, coada = m.group(1), m.group(2), m.group(3), m.group(4)
        if "<" + tag in corp.lower() or len(corp.strip()) < 12:
            return m.group(0)
        c1 = leaga_fraze(corp)
        if c1 != corp:
            n[1] += 1
        c2 = leaga_final(c1)
        if c2 != c1:
            n[0] += 1
        return cap + c2 + coada

    return BLOC.sub(per, h), n


def leaga_pagina(h):
    """Intoarce (html, [n_final, n_fraze]). Sare peste continutul din <script> si <style>."""
    tot = [0, 0]
    parti = re.split(r"(<script[\s\S]*?</script>|<style[\s\S]*?</style>)", h)
    for i in range(0, len(parti), 2):
        parti[i], n = rescrie(parti[i])
        tot[0] += n[0]
        tot[1] += n[1]
    return "".join(parti), tot


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--doar", default="**/*.html",
                    help="tipar glob relativ la repo; implicit tot situl")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    tot, fis = [0, 0], 0
    for fp in sorted(glob.glob(os.path.join(a.repo, a.doar), recursive=True)):
        h = open(fp, encoding="utf-8").read()
        h2, n = leaga_pagina(h)
        tot[0] += n[0]
        tot[1] += n[1]
        if h2 != h:
            fis += 1
            if a.apply:
                open(fp, "w", encoding="utf-8", newline="\n").write(h2)
    print(f"pas_asezare: {tot[0]} blocuri cu finalul legat, {tot[1]} cu inceputul de fraza legat, "
          f"{fis} fisiere  ({'APLICAT' if a.apply else 'PROBA'})")
