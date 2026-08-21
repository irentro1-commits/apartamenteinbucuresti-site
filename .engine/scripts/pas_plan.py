#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PLANSA DE PE PAGINA APARTAMENTULUI: fisa noastra, in locul planului v4.

Andy, 21 aug 2026, cu pagina lui ap. 7 deschisa: *"refa alea in cod sau din nou cumva ca poti
asta, refa de la 0 daca e nevoie sa arate mai bine si curat"*, si imediat dupa:
*"si am intrat pe site si tot ala vechi il vad"*.

CE INLOCUIESTE. Planul v4 are un antet, o randare si o banda cu trei cifre. Fisa are, in plus,
suprafata FIECAREI CAMERE, pozitia in etaj cu busola si strada, si dotarile. Se genereaza in
`_fise/build_fise.py`, cate una pe apartament si pe limba, si se publica sub
`/planuri/fise/plan-ap-N-<limba>-v5.webp`.

DE CE E UN PAS DE PIPELINE, si nu o cautare-si-inlocuire facuta o data. Paginile de apartament
sunt scrise de mana, dar legea motorului e ca HTML-ul generat nu se atinge cu scripturi
one-shot: ori intra in sursa, ori devine un pas. Asta e pasul. Ruleaza de cate ori vrei:
a doua rulare nu schimba nimic.

CE NU FACE. Nu inventeaza imagini. Daca un apartament nu are fisa in manifest, pagina lui
ramane exact cum e, cu planul vechi, si pasul o numara la "neatinse". O pagina cu imagine
lipsa e mai rea decat una cu imagine veche.

    python3 pas_plan.py --repo <cale>
    python3 pas_plan.py --repo <cale> --apply
"""
import argparse
import glob
import io
import json
import os
import re

# subtitrarea spune de unde vin cifrele, in limba paginii. Numerele raman in text, nu doar in
# imagine: un motor de cautare nu citeste suprafetele dintr-un webp.
# Andy, 21 aug 2026, aratand subtitrarea: *"aici sa pui clar Planul dezvoltatorului si atat"*.
# Scrisesem "Fisa i-vory, dupa planul dezvoltatorului si grila lui de preturi", crezand ca
# lamuresc de unde vin cifrele. Lamuream de fapt cine a facut plansa, ceea ce pe pagina unui
# apartament nu intereseaza pe nimeni si suna a semnatura pusa pe munca altuia: desenul e al
# dezvoltatorului, noi doar l-am asezat. Ebraica, araba si ucraineana spuneau deja simplu
# "Plan de la dezvoltator"; romana si engleza s-au aliniat la ele.
LEGENDA = {
    "ro": ("Planul dezvoltatorului. "
           "Suprafață utilă <b>%(utila)s mp</b>, terasă <b>%(terasa)s mp</b>, "
           "total <b>%(total)s mp</b>. Mobilierul e orientativ."),
    "en": ("The developer's floor plan. "
           "Usable area <b>%(utila)s sqm</b>, terrace <b>%(terasa)s sqm</b>, "
           "total <b>%(total)s sqm</b>. Furniture is indicative."),
}
LUPA = {"ro": "Deschide fișa la dimensiune mare", "en": "Open the sheet at full size"}

LAT, INALT = 1720, 1180


def limba_din_cale(rel):
    p = rel.replace("\\", "/").split("/")[0]
    return p if p in ("en", "he", "ar", "uk") else "ro"


def imaginea(limba):
    """Ebraica, araba si ucraineana folosesc plansa engleza: asa era si cu v4, si nu are rost
    sa generam patru imagini identice ca desen si diferite doar prin alfabet."""
    return "ro" if limba == "ro" else "en"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    man_cale = os.path.join(a.repo, "planuri", "fise", "index.json")
    if not os.path.exists(man_cale):
        print("pas_plan: nu exista manifestul fiselor, nu ating nimic")
        return 0
    man = json.load(io.open(man_cale, encoding="utf-8"))

    schimbate = neatinse = 0
    for fp in sorted(glob.glob(os.path.join(a.repo, "**", "apartamente", "*", "index.html"),
                               recursive=True)):
        rel = os.path.relpath(fp, a.repo)
        nume = os.path.basename(os.path.dirname(fp))
        if "-ap-" not in nume:
            continue
        nr = nume.rsplit("-ap-", 1)[1]
        lb = limba_din_cale(rel)
        cheie = "%s-%s" % (nr, imaginea(lb))
        nou = man.get(cheie)
        if not nou:
            neatinse += 1
            continue

        h = io.open(fp, encoding="utf-8").read()
        vechi = "/planuri/plan-ap-%s-%s-v4.webp" % (nr, imaginea(lb))
        if vechi not in h and nou not in h:
            neatinse += 1
            continue

        orig = h
        h = h.replace(vechi, nou)

        # dimensiunile trebuie sa fie ale imaginii NOI, altfel pagina isi rezerva alt loc si
        # continutul de dedesubt sare cand se incarca plansa
        h = re.sub(r'(<img src="' + re.escape(nou) + r'" )width="\d+" height="\d+"',
                   r'\g<1>width="%d" height="%d"' % (LAT, INALT), h)

        # subtitrarea: aceleasi cifre, alta sursa declarata
        g = man.get("suprafete", {}).get(nr)
        if g and lb in LEGENDA:
            h = re.sub(r"(<figcaption>).*?(<br>)",
                       lambda m: m.group(1) + (LEGENDA[lb] % g) + m.group(2), h, count=1,
                       flags=re.S)
            h = re.sub(r'(<a class="lupa"[^>]*>)[^<]*(&rarr;)',
                       lambda m: m.group(1) + LUPA[lb] + " " + m.group(2), h, count=1)

        if h != orig:
            schimbate += 1
            if a.apply:
                io.open(fp, "w", encoding="utf-8", newline="\n").write(h)
        else:
            neatinse += 1

    print("pas_plan: %d pagini pe fisa noua, %d neatinse  (%s)"
          % (schimbate, neatinse, "APLICAT" if a.apply else "PROBA"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
