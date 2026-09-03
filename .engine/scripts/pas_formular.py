#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PASUL FORMULAR: a doua usa de contact, langa butonul de WhatsApp.

DE CE EXISTA. Masurat pe 20 aug 2026, pe tot repo-ul: 192 de pagini HTML si **zero** elemente
`<form>`, zero `<input>`. Singura cale de a vorbi cu noi era WhatsApp. WhatsApp e o usa buna,
dar e usa cu pragul cel mai mare din toate: cere omului sa isi dea numarul de telefon unui
necunoscut, instant, inainte sa stie ceva despre noi, si sa fie pe dispozitivul cu aplicatia
instalata. Cine nu vrea, nu poate, sau nu e inca pregatit pleca fara sa lase nimic, fiindca
nu avea unde. Blocul asta e locul unde poate lasa.

DE CE E PAS DE PIPELINE SI NU SCRIPT ONE-SHOT (aceeasi lectie ca la pas_dif, 10 aug 2026):
coaja paginilor de blog en/he/ar/uk se ia la fiecare regenerare din `<lang>/preturi/index.html`.
Daca formularul ar fi injectat cu un script din /tmp, prima regenerare l-ar sterge de pe blog
in patru limbi, tacut, si `verifica_fidelitate.py` s-ar face rosu fara ca nimeni sa stie de ce.
Un pas care atinge HTML-ul generat traieste in pipeline. Altfel e o bomba cu ceas.

ORDINEA: dupa `pas_dif`, inainte de `pas_asezare`. pas_asezare leaga cuvinte din textul FINAL,
deci orice pas care mai adauga text dupa el lasa legaturi pe fraze care nu mai exista.

Idempotent: sare peste paginile care au deja blocul. Rulat de doua ori la rand da 0 modificari.

    python3 pas_formular.py --repo /tmp/apt --doar "**/*.html"            # proba
    python3 pas_formular.py --repo /tmp/apt --doar "**/*.html" --apply    # aplica
"""
import argparse, glob, html, json, os, re

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = json.load(open(os.path.join(ENGINE, "date", "formular.json"), encoding="utf-8"))

# Cheia Web3Forms. NU e secret: traieste oricum in HTML-ul public, exact ca pe i-vory.studio.
# Ea decide in ce cutie postala ajung cererile. Azi e cutia i-vory Studio, adica acolo unde se
# uita Andy. Cand Ilioara primeste adresa ei, se schimba AICI, intr-un singur loc, si se
# regenereaza. Nicaieri altundeva.
CHEIE = "826056ec-19c9-49f6-b07f-2dda086e6887"

CSS = '<link rel="stylesheet" href="/assets/formular-v2.css">'
JS = '<script src="/assets/formular-v1.js" defer></script>'
ANCORA_CSS = '<link rel="stylesheet" href="/assets/pagini-v35.css">'

MARCA = 'class="lf rv"'


def lang_of(h):
    m = re.search(r'<html[^>]*lang="([a-z]{2})"', h)
    return m.group(1) if m else "ro"


def cale_publica(fp, repo):
    """/apartamente/ap-7/index.html -> /apartamente/ap-7/ ; index.html din radacina -> /"""
    rel = os.path.relpath(fp, repo).replace(os.sep, "/")
    if rel.endswith("/index.html"):
        rel = rel[: -len("index.html")]
    elif rel == "index.html":
        rel = ""
    return "/" + rel


def titlu_pagina(h):
    """<h1> curatat de tag-uri, pentru subiectul emailului. Ca sa se vada din lista de mesaje
    despre ce apartament e vorba, fara sa deschizi mesajul."""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
    if not m:
        return ""
    t = re.sub(r"<[^>]+>", " ", m.group(1))
    t = html.unescape(t).replace(" ", " ")
    return re.sub(r"\s+", " ", t).strip()[:90]


def bloc(l, cale, titlu):
    c = T[l]
    subiect = f"Ilioara: cerere noua de pe {cale}" + (f" ({titlu})" if titlu else "")
    a = html.escape
    return (
        f'\n<div {MARCA} data-fx="rise">'
        f'<h3 class="lf-t">{c["titlu"]}</h3>'
        f'<p class="lf-s">{c["sub"]}</p>'
        f'<form class="lf-f" action="https://api.web3forms.com/submit" method="POST">'
        f'<input type="hidden" name="access_key" value="{CHEIE}">'
        f'<input type="hidden" name="subject" value="{a(subiect)}">'
        f'<input type="hidden" name="from_name" value="apartamenteinbucuresti.ro">'
        f'<input type="hidden" name="pagina" value="{a(cale)}">'
        f'<div class="lf-row">'
        f'<div><label class="lf-l" for="lf-n">{c["nume"]}</label>'
        f'<input class="lf-i" id="lf-n" name="nume" type="text" required'
        f' autocomplete="name" placeholder="{a(c["numePh"])}"></div>'
        f'<div><label class="lf-l" for="lf-c">{c["contact"]}</label>'
        f'<input class="lf-i" id="lf-c" name="contact" type="text" required'
        f' autocomplete="email" placeholder="{a(c["contactPh"])}"></div>'
        f"</div>"
        f'<label class="lf-l" for="lf-m">{c["mesaj"]}</label>'
        f'<textarea class="lf-i" id="lf-m" name="mesaj" rows="3"'
        f' placeholder="{a(c["mesajPh"])}"></textarea>'
        f'<input class="lf-hp" type="checkbox" name="botcheck" tabindex="-1"'
        f' autocomplete="off" aria-hidden="true">'
        f'<button class="btn lf-b" type="submit" data-trimit="{a(c["trimit"])}">'
        f'{c["buton"]}</button>'
        f'<p class="lf-legal">{c["legal"]} '
        f'<a href="/informatii-legale/">{c["legalLink"]}</a>.</p>'
        f"</form>"
        f'<div class="lf-msg lf-ok"><h4>{c["okT"]}</h4><p>{c["okP"]}</p></div>'
        f'<div class="lf-msg lf-ero"><h4>{c["eroT"]}</h4><p>{c["eroP"]}</p></div>'
        f"</div>\n"
    )


def sfarsit_pcta(h, start):
    """Capatul blocului .pcta, numarand div-urile deschise. Nu se cauta primul </div>:
    blocul contine div-uri interioare pe unele pagini, iar un </div> gresit ar muta formularul
    in mijlocul butonului."""
    i, adanc = start, 0
    for m in re.finditer(r"<div\b|</div>", h[start:]):
        adanc += 1 if m.group(0) == "<div" else -1
        i = start + m.end()
        if adanc == 0:
            return i
    return -1


def injecteaza(h, cale):
    """Intoarce (html, s_a_schimbat). Ancora: imediat DUPA blocul .pcta, adica exact acolo unde
    pagina deja cere contactul. Nu inaintea lui: WhatsApp ramane prima usa, formularul e a doua,
    pentru cine nu vrea prima."""
    if MARCA in h or "<main" not in h:
        return h, False
    m = re.search(r'<div class="pcta\b[^"]*"[^>]*>', h)
    if not m:
        return h, False
    poz = sfarsit_pcta(h, m.start())
    if poz < 0:
        return h, False

    l = lang_of(h)
    if l not in T:
        l = "ro"
    h = h[:poz] + bloc(l, cale, titlu_pagina(h)) + h[poz:]

    if CSS not in h:
        if ANCORA_CSS in h:
            h = h.replace(ANCORA_CSS, ANCORA_CSS + "\n" + CSS, 1)
        else:
            h = h.replace("</head>", CSS + "\n</head>", 1)
    if JS not in h:
        h = h.replace("</body>", JS + "\n</body>", 1)
    return h, True


def scoate(h):
    """Scoate blocul, ca sa poata fi pus la loc proaspat. Nu e o functie de curatenie: e
    singura cale onesta de a REIMPROSPATA blocul cand se schimba ceva ce el a copiat din
    pagina. Subiectul emailului contine <h1>-ul paginii; daca titlul se rescrie si blocul
    ramane pe loc, subiectul minte despre pagina din care a venit cererea.
    Aceeasi numaratoare de div-uri ca la injectare, nu primul </div> gasit."""
    i = h.find("<div " + MARCA)
    if i < 0:
        return h, False
    j = sfarsit_pcta(h, i)
    if j < 0:
        return h, False
    # inghite si randul gol pe care l-a lasat injectarea, ca sa iasa fisier identic
    inc = i - 1 if i > 0 and h[i - 1] == "\n" else i
    sf = j + 1 if h[j:j + 1] == "\n" else j
    return h[:inc] + h[sf:], True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--doar", default="**/*.html",
                    help="tipar glob relativ la repo; implicit tot situl")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--reimprospateaza", action="store_true",
                    help="scoate blocul si il pune la loc, cu textul de azi al paginii")
    a = ap.parse_args()

    if a.reimprospateaza:
        n = 0
        for fp in sorted(glob.glob(os.path.join(a.repo, a.doar), recursive=True)):
            h = open(fp, encoding="utf-8").read()
            h2, s = scoate(h)
            if s:
                n += 1
                if a.apply:
                    open(fp, "w", encoding="utf-8", newline="\n").write(h2)
        print(f"pas_formular: {n} blocuri scoase pentru reimprospatare "
              f"({'APLICAT' if a.apply else 'PROBA'})")
        raise SystemExit(0)

    pus = sarit = 0
    for fp in sorted(glob.glob(os.path.join(a.repo, a.doar), recursive=True)):
        h = open(fp, encoding="utf-8").read()
        h2, schimbat = injecteaza(h, cale_publica(fp, a.repo))
        if schimbat:
            pus += 1
            if a.apply:
                open(fp, "w", encoding="utf-8", newline="\n").write(h2)
        elif MARCA not in h and "<main" in h:
            sarit += 1
            print(f"  fara ancora .pcta: {os.path.relpath(fp, a.repo)}")
    print(f"pas_formular: {pus} formulare puse, {sarit} pagini fara ancora  "
          f"({'APLICAT' if a.apply else 'PROBA'})")
