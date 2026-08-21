#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REPERELE PAGINII: butonul plutitor de contact intra pe harta, nu langa ea.

CE ERA. `axe-core` raporta regula `region` pe 19 elemente, iar dupa ce am reparat landingul
a ramas unul singur, dar exact ala care nu trebuia: `.pmcta`, butonul plutitor de WhatsApp,
pe 197 de pagini. Statea copil direct al lui `<body>`, in afara oricarui reper.

DE CE CONTEAZA AICI, SI NU E O BIFA. Cine foloseste un cititor de ecran nu deruleaza pagina,
ci sare din reper in reper: antet, continut, navigatie, subsol. Un element care nu e in
niciun reper nu apare in lista aia. Butonul care aduce mesajele era singurul lucru de pe
pagina invizibil in modul asta de navigare. Andy a intrebat cum primim mai multe mesaje: una
dintre caile ca omul sa NU scrie e sa nu gaseasca unde.

CE FACE. Pune `role="complementary"` si un nume citit, in limba paginii. Nu schimba eticheta,
nu schimba clasa, nu muta nimic in pagina: un reper e o promisiune facuta cititorului de
ecran, si atat. Vizual, zero diferenta.

DE CE `complementary` SI NU `region`. `region` cere ca lucrul sa fie o sectiune de continut;
un buton plutitor nu e. `complementary` inseamna exact ce e: ceva de sine statator, legat de
pagina, dar pe langa ea.

    python3 pas_repere.py --repo <cale>
    python3 pas_repere.py --repo <cale> --apply
"""
import argparse
import glob
import io
import os

VECHI = '<div class="pmcta">'

# Numele citit, in limba paginii. Nu e "buton WhatsApp": cititorul spune deja ca e legatura.
# Se spune CE FACE pentru om, cu verbul pe care il foloseste tot situl.
NUME = {
    "ro": "Scrieți-ne rapid",
    "en": "Quick contact",
    "he": "יצירת קשר מהירה",
    "ar": "تواصل سريع",
    "uk": "Швидкий контакт",
}

# Landingul: filmul, voalul si ecranul de incarcare stau copii directi ai lui `body`.
# Filmul primeste reper cu nume; voalul e doar o pictura peste el, deci iese din citire;
# ecranul de incarcare primeste `status`, care e forma corecta pentru "se intampla ceva
# acum", iar procentul din el se ascunde ca sa nu fie citit din nou la fiecare cifra.
FILM = {
    "ro": "Filmul ansamblului", "en": "The building film",
    "he": "סרטון הפרויקט", "ar": "فيلم المجمّع", "uk": "Фільм про комплекс",
}
INCARCA = {
    "ro": "Se încarcă", "en": "Loading",
    "he": "טוען", "ar": "جارٍ التحميل", "uk": "Завантаження",
}


def limba(rel):
    for parte in rel.replace("\\", "/").split("/"):
        if parte in ("en", "he", "ar", "uk"):
            return parte
    return "ro"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    atinse = sarite = 0
    for fp in sorted(glob.glob(os.path.join(a.repo, "**", "*.html"), recursive=True)):
        rel = os.path.relpath(fp, a.repo)
        if rel.replace("\\", "/").startswith(".engine/"):
            continue
        h = io.open(fp, encoding="utf-8").read()
        lb = limba(rel)

        # Fiecare reparatie e independenta si idempotenta: se aplica daca forma VECHE mai e
        # in pagina, si nu face nimic daca a fost deja pusa. O garda comuna pe prima dintre
        # ele ar sari peste restul de indata ce prima e reparata, si exact asta s-a intamplat
        # la rularea de dinainte: 0 pagini atinse, cu trei reparatii inca nefacute.
        nou = h
        for vechi, pus in (
            (VECHI, '<div class="pmcta" role="complementary" aria-label="%s">' % NUME[lb]),
            ('<div id="stage"><canvas',
             '<div id="stage" role="region" aria-label="%s"><canvas' % FILM[lb]),
            ('<div id="scrim"></div>', '<div id="scrim" aria-hidden="true"></div>'),
            ('<div id="load"><', '<div id="load" role="status" aria-label="%s"><' % INCARCA[lb]),
            ('<div class="p" id="pct">', '<div class="p" id="pct" aria-hidden="true">'),
        ):
            if vechi in nou:
                nou = nou.replace(vechi, pus)

        if nou == h:
            sarite += 1
            continue
        atinse += 1
        if a.apply:
            io.open(fp, "w", encoding="utf-8", newline="\n").write(nou)

    print("pas_repere: %d pagini cu reperele puse la punct, %d sarite  (%s)"
          % (atinse, sarite, "APLICAT" if a.apply else "PROBA"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
