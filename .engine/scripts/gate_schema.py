#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GATE SCHEMA: fiecare proprietate pe tipul care o admite, fiecare valoare in intervalul ei.

    python3 gate_schema.py --repo /tmp/apt
    python3 gate_schema.py --repo /tmp/apt --vocab /tmp/schemaorg.jsonld

DE CE EXISTA. Search Console, 10 aug 2026: **"Invalid object type for field '<parent_node>'"**,
6 pagini, item "Ilioara Residence". Mesajul lui Google spune CE nu-i place, dar nu spune UNDE:
`<parent_node>` inseamna "obiectul asta, in slotul in care l-ai pus", si atat. Cu ochiul, cele
6 pagini afectate si cele curate arata identic, deci cautarea din priviri nu duce nicaieri.

Asa ca nu ghicim: luam vocabularul schema.org (`schemaorg-current-https.jsonld`) si verificam
mecanic, pentru fiecare bloc JSON-LD din sit:

  1. DOMENIU  proprietatea e definita pe tipul asta, sau pe un stramos al lui?
              `provider` NU exista pe `Place`, deci nici pe `ApartmentComplex`, care mosteneste
              din `Residence` -> `Place`. Scris acolo, e o proprietate care nu are ce cauta.
  2. INTERVAL tipul valorii e in `rangeIncludes` al proprietatii, sau subtip al unuia dintre ele?
              Asta e exact intrebarea din mesajul lui Google: "invalid OBJECT TYPE for field".

Referintele prin `@id` catre un nod definit in ALT bloc din aceeasi pagina se rezolva inainte
de verificare: altfel fiecare `{"@id": ...}` ar parea un obiect fara tip.

Vocabularul se ia o data si se tine local. Fara el, gate-ul iese cu SKIP, nu cu PASS: un gate
care nu poate masura trebuie sa spuna asta, nu sa taca verde.
"""
import argparse, glob, json, os, re, sys, urllib.request

VOCAB_URL = "https://schema.org/version/latest/schemaorg-current-https.jsonld"
S = "https://schema.org/"


def incarca_vocab(cale):
    if not os.path.exists(cale):
        try:
            urllib.request.urlretrieve(VOCAB_URL, cale)
        except Exception as e:
            print(f"SKIP: nu pot lua vocabularul schema.org ({e}).")
            print(f"      Ia-l manual si da-l cu --vocab:  curl -o {cale} {VOCAB_URL}")
            return None
    g = json.load(open(cale, encoding="utf-8"))["@graph"]

    def lst(x):
        if x is None: return []
        return x if isinstance(x, list) else [x]

    def nume(x):
        return (x.get("@id") if isinstance(x, dict) else x).replace("schema:", "").split("/")[-1]

    parinti, dom, rng, tipuri, props = {}, {}, {}, set(), set()
    for n in g:
        t = lst(n.get("@type"))
        i = nume(n)
        if "rdfs:Class" in t or "Class" in [str(x).split(":")[-1] for x in t]:
            tipuri.add(i)
            parinti[i] = [nume(x) for x in lst(n.get("rdfs:subClassOf"))]
        if "rdf:Property" in t or "Property" in [str(x).split(":")[-1] for x in t]:
            props.add(i)
            dom[i] = {nume(x) for x in lst(n.get("schema:domainIncludes"))}
            rng[i] = {nume(x) for x in lst(n.get("schema:rangeIncludes"))}
    return dict(parinti=parinti, dom=dom, rng=rng, tipuri=tipuri, props=props)


def stramosi(t, parinti, vazut=None):
    vazut = vazut or set()
    if t in vazut: return vazut
    vazut.add(t)
    for p in parinti.get(t, []):
        stramosi(p, parinti, vazut)
    return vazut


def blocuri(html):
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            yield json.loads(m.group(1))
        except Exception as e:
            yield {"__eroare_json__": str(e)}


def verifica_pagina(html, V):
    """Intoarce lista de (tip, proprietate, motiv)."""
    noduri = [b for b in blocuri(html)]
    # harta @id -> tip, ca sa putem rezolva referintele dintre blocuri
    tip_dupa_id = {}

    def indexeaza(o):
        if isinstance(o, dict):
            if o.get("@id") and o.get("@type"):
                tip_dupa_id[o["@id"]] = o["@type"]
            for v in o.values():
                indexeaza(v)
        elif isinstance(o, list):
            for v in o: indexeaza(v)

    for n in noduri: indexeaza(n)

    gasite = []

    def tip_valorii(v):
        if isinstance(v, dict):
            if v.get("@type"): return v["@type"]
            if v.get("@id"):   return tip_dupa_id.get(v["@id"])   # None = referinta nerezolvata
            return None
        return "__literal__"

    def merge(tv, permise):
        """Tipul valorii se potriveste cu intervalul? Literalele se accepta pe orice interval
        care contine un tip de date sau Text/URL: Google e permisiv acolo, si nu vrem zgomot."""
        if tv == "__literal__":
            return True
        if tv is None:
            return True          # referinta pe alta pagina: nu o putem judeca, nu o acuzam
        anc = stramosi(tv, V["parinti"])
        return bool(anc & permise)

    def umbla(o, tip_parinte=None):
        if isinstance(o, list):
            for v in o: umbla(v, tip_parinte)
            return
        if not isinstance(o, dict): return
        if "__eroare_json__" in o:
            gasite.append(("(bloc)", "(JSON)", "JSON invalid: " + o["__eroare_json__"]))
            return
        # UN NOD POATE AVEA MAI MULTE TIPURI, si atunci o proprietate e valida daca o admite
        # MACAR UNUL dintre ele. Fara asta, gate-ul raporta `Apartment.offers` pe noduri scrise
        # ["Apartment","Product"], adica exact reparatia pe care tocmai o cerusem: Apartment
        # ramane locuinta, Product ii da `offers`. Un gate care nu intelege reparatia proprie
        # e un gate care te invata sa-l ignori.
        tt = o.get("@type")
        tt = [x for x in (tt if isinstance(tt, list) else [tt]) if x]
        t = tt[0] if tt else None
        cunoscute = [x for x in tt if x in V["tipuri"]]
        anc = set()
        for x in cunoscute:
            anc |= stramosi(x, V["parinti"])
        for k, v in o.items():
            if k.startswith("@"): continue
            if cunoscute:
                if k not in V["props"]:
                    gasite.append(("+".join(cunoscute), k, "proprietate inexistenta in schema.org"))
                else:
                    if V["dom"].get(k) and not (anc & V["dom"][k]):
                        gasite.append(("+".join(cunoscute), k,
                                       f"proprietate nedefinita pe {'+'.join(cunoscute)} "
                                       f"(admisa pe: {', '.join(sorted(V['dom'][k])[:4])})"))
                    else:
                        for val in (v if isinstance(v, list) else [v]):
                            tv = tip_valorii(val)
                            if V["rng"].get(k) and not merge(tv, V["rng"][k]):
                                gasite.append(("+".join(cunoscute), k,
                                               f"valoare de tip {tv}, dar campul cere "
                                                     f"{', '.join(sorted(V['rng'][k])[:4])}"))
            umbla(v, t)

    for n in noduri: umbla(n)
    return gasite


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--vocab", default="/tmp/schemaorg.jsonld")
    ap.add_argument("--max", type=int, default=0, help="cate defecte se accepta")
    a = ap.parse_args()

    V = incarca_vocab(a.vocab)
    if V is None:
        return 0

    print("=" * 78)
    print("SCHEMA — proprietatea pe tipul care o admite, valoarea in intervalul ei")
    print("=" * 78)

    dupa_defect, pagini_rele = {}, set()
    fisiere = sorted(glob.glob(os.path.join(a.repo, "**", "index.html"), recursive=True))
    for fp in fisiere:
        rel = os.path.relpath(fp, a.repo)
        for tip, prop, motiv in verifica_pagina(open(fp, encoding="utf-8").read(), V):
            dupa_defect.setdefault((tip, prop, motiv), []).append(rel)
            pagini_rele.add(rel)

    if not dupa_defect:
        print(f"  {len(fisiere)} pagini, zero defecte de schema.\n  VERDICT: PASS")
        return 0

    for (tip, prop, motiv), pagini in sorted(dupa_defect.items(), key=lambda x: -len(x[1])):
        print(f"\n  {len(pagini):4} pagini · {tip}.{prop}")
        print(f"       {motiv}")
        print(f"       ex: {', '.join(pagini[:3])}")
    total = sum(len(p) for p in dupa_defect.values())
    print(f"\n{'-' * 78}")
    print(f"  {total} aparitii, pe {len(pagini_rele)} din {len(fisiere)} pagini")
    print(f"  VERDICT: {'PASS' if total <= a.max else 'FAIL'}")
    return 0 if total <= a.max else 1


if __name__ == "__main__":
    raise SystemExit(main())
