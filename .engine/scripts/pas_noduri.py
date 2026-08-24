#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NODURILE DE ENTITATE: un `@id` referit trebuie sa fie DEFINIT pe aceeasi pagina.

    python3 pas_noduri.py --repo <cale>                      # arata, nu scrie
    python3 pas_noduri.py --repo <cale> --apply
    python3 pas_noduri.py --repo <cale> --doar "**/blog/**/index.html" --apply

DE CE EXISTA, si e singurul lucru important din fisierul asta.

Pe 24 aug 2026, `gate_graf.py` (poarta noua de INTEGRITATE a grafului, nu de sintaxa) a gasit
pe toate paginile de apartament un `Offer.seller` care trimite prin `@id` catre
`https://apartamenteinbucuresti.ro/#organization`, nod care nu e definit pe acele pagini.
Adica **fiecare oferta de pe situl de vanzare era fara vanzator**. Masurat pe tot repo-ul:
150 de pagini din 211 aveau cel putin o trimitere care nu ducea nicaieri.

    65 pagini  Offer.seller              -> #organization   (13 apartamente x 5 limbi)
    70 pagini  BlogPosting.isPartOf      -> #residence      (14 articole x 5 limbi)
     5 pagini  Blog.publisher            -> #organization   (indexul de blog)
     5 pagini  AggregateOffer.seller     -> #organization   (/preturi/)
     5 pagini  Person.makesOffer.seller  -> #organization   (/echipa-ilioara-residence/)

CAUZA RADACINA, gasita in comit, nu presupusa: `d5ed8f36`, 10 aug 2026. Comitul acela repara
o eroare reala semnalata de Search Console si muta legatura cu firma de pe
`ApartmentComplex.provider` pe `Offer.seller`, care e campul corect. A scris-o insa ca
trimitere goala, `{"@id": ".../#organization"}`, pe pagini SCRISE DE MANA, unde nodul
`#organization` nu existase niciodata. `gate_schema.py` a dat PASS fiindca tipul si campul
erau corecte. Nimeni nu masura daca trimiterea ajunge undeva.

    Un validator de SINTAXA si un validator de INTEGRITATE sunt doua unelte diferite.

DE CE E UN PAS DIN PIPELINE, si nu un script one-shot din /tmp. Legea repo-ului, scrisa cu
pretul din 10 august: *nicio modificare pe HTML-ul generat facuta direct, cu un script
one-shot*. Ori intra in sursa, ori devine un `pas_*.py` pornit din `publica.py`. Altfel prima
regenerare de blog sterge nodurile injectate si nimeni nu afla pana la urmatoarea rulare a
portii. Rulat din `publica.py`, `verifica_fidelitate.py` il tine in viata.

CE PUNE, SI DE CE ATAT. Nodurile canonice stau in `.engine/date/noduri.json`, un singur loc.
Nodul injectat poarta identitatea (tip, @id, nume, url) plus ce se poate sustine pe orice
pagina: logo, imagine, zona servita, punct de contact, sameAs, iar pentru cladire coordonatele.
**Nu poarta adresa cu numar.** `streetAddress` e afirmatie tare la politica Google (nu se
marcheaza ce nu se vede), iar pe paginile de blog adresa apare fara numar. Adresa completa
ramane pe pagina de acasa, unde e vizibila; Google uneste entitatile dupa `@id`.

CE SCOATE. `geo` si `hasMap` sunt proprietati de `Place`, nu de `Organization`. Erau puse pe
`#organization` pe 10 pagini si `gate_schema.py` cadea in CI cu 20 de aparitii. Coordonatele
traiesc pe `#residence`, care chiar e un Place.

REGULA DE SIGURANTA: un bloc JSON-LD existent se rescrie NUMAI daca, nemodificat, se
re-serializeaza octet cu octet identic. Daca nu, pagina e sarita si spusa pe nume. Situl are
doua stiluri de json.dumps in HTML (compact si cu spatii) si niciunul nu are voie sa se
schimbe: fidelitatea se masoara octet cu octet.
"""
import argparse
import glob
import json
import os
import re

SCRIPT = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                    re.S | re.I)


def incarca_noduri(engine):
    cale = os.path.join(os.path.dirname(engine), "date", "noduri.json")
    with open(cale, encoding="utf-8") as f:
        d = json.load(f)
    return d["noduri"], d.get("scoate", {})


def _plimba(o, f):
    if isinstance(o, dict):
        f(o)
        for v in o.values():
            _plimba(v, f)
    elif isinstance(o, list):
        for v in o:
            _plimba(v, f)


def citeste_graf(htm):
    """(definite, referite) -- @id-uri definite pe pagina si @id-uri doar referite."""
    definite, referite = set(), set()
    for brut in SCRIPT.findall(htm):
        try:
            d = json.loads(brut)
        except ValueError:
            continue

        def vezi(n):
            i = n.get("@id")
            if not i:
                return
            if list(n.keys()) == ["@id"]:
                referite.add(i)
            else:
                definite.add(i)

        _plimba(d, vezi)
    return definite, referite


def stil(brut):
    """Separatorii cu care a fost scris blocul. Situl are ambele stiluri; nu se amesteca."""
    return (", ", ": ") if '", "' in brut or '": "' in brut else (",", ":")


def scrie(d, brut):
    return json.dumps(d, ensure_ascii=False, separators=stil(brut))


def loc_de_pus(htm):
    """Dupa ULTIMUL bloc ld+json din pagina. Ordinea blocurilor nu conteaza pentru parser,
    dar un loc fix o face reproductibila, deci si idempotenta."""
    ultim = None
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>.*?</script>',
                         htm, re.S | re.I):
        ultim = m
    return ultim.end() if ultim else None


def repara(htm, noduri, scoate):
    """Intoarce (html_nou, [ce s-a facut], [avertismente])."""
    facut, atentie = [], []

    # 1. SCOATE proprietatile care nu au ce cauta pe tipul nodului
    for ident, chei in scoate.items():
        for m in list(SCRIPT.finditer(htm)):
            brut = m.group(1).strip()
            if ident not in brut:
                continue
            try:
                d = json.loads(brut)
            except ValueError:
                continue
            if d.get("@id") != ident or list(d.keys()) == ["@id"]:
                continue
            if not any(k in d for k in chei):
                continue
            if scrie(d, brut) != brut:
                atentie.append("bloc %s nu se re-serializeaza identic, sarit" % ident)
                continue
            for k in chei:
                d.pop(k, None)
            nou = scrie(d, brut)
            htm = htm[:m.start(1)] + nou + htm[m.end(1):]
            facut.append("scos %s de pe %s" % ("+".join(chei), ident.rsplit("#", 1)[-1]))

    # 2. PUNE nodurile referite dar nedefinite
    definite, referite = citeste_graf(htm)
    lipsa = [i for i in sorted(noduri) if i in referite and i not in definite]
    if lipsa:
        poz = loc_de_pus(htm)
        if poz is None:
            atentie.append("pagina refera %s dar nu are niciun bloc ld+json" % ", ".join(lipsa))
        else:
            bucata = ""
            for i in lipsa:
                bucata += ('\n<script type="application/ld+json">'
                           + json.dumps(noduri[i], ensure_ascii=False) + "</script>")
                facut.append("pus " + i.rsplit("#", 1)[-1])
            htm = htm[:poz] + bucata + htm[poz:]
    return htm, facut, atentie


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--doar", default="**/*.html",
                    help="glob recursiv peste repo, ca la ceilalti pasi")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    engine = os.path.dirname(os.path.abspath(__file__))
    noduri, scoate = incarca_noduri(engine)

    # glob recursiv, ca la pas_dif si pas_asezare: `**` nu intra in foldere ascunse, deci
    # `.engine`, `.git` si `.github` raman pe dinafara fara nicio lista de excluderi.
    schimbate, toate_atentie, total = 0, [], 0
    for cale in sorted(glob.glob(os.path.join(a.repo, a.doar), recursive=True)):
        if not cale.endswith(".html"):
            continue
        rel = os.path.relpath(cale, a.repo).replace(os.sep, "/")
        total += 1
        with open(cale, encoding="utf-8") as f:
            htm = f.read()
        nou, facut, atentie = repara(htm, noduri, scoate)
        for w in atentie:
            toate_atentie.append("%s: %s" % (rel, w))
        if nou == htm:
            continue
        schimbate += 1
        print("  %-64s %s" % (rel, ", ".join(facut)))
        if a.apply:
            with open(cale, "w", encoding="utf-8", newline="") as f:
                f.write(nou)

    for w in toate_atentie:
        print("  ATENTIE  " + w)
    verb = "reparate" if a.apply else "de reparat (fara --apply nu s-a scris nimic)"
    print("noduri de entitate: %d pagini %s, din %d citite" % (schimbate, verb, total))
    return 1 if toate_atentie else 0


if __name__ == "__main__":
    raise SystemExit(main())
