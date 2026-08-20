#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HOMEPAGE: contorul de disponibilitate si bara de ocupare, in banda copertei.

Andy, 21 aug 2026: *"vreau sa modifici si homepage-ul sa se vada clar ca mai sunt 7-8
apartamente disponibile si un progress bar in care se vede gradul de ocupare/vanzare"*.

DE CE IN BANDA COPERTEI, si nu in coloana editoriala sau intr-un `beat`. Coloana editoriala
e centrata pe verticala: orice inaltime adaugata urca continutul cu jumatate, iar la 1366x700
kickerul auriu intra PESTE logo. Masurat: distanta pana la antet trece de la +8px la -47px.
Banda e ancorata jos si creste in sus, in golul care exista deja, deci zero regresie sus.
Iar `beat`-urile sunt `position:fixed` si se vad doar intr-o fereastra de scroll din film:
cifra pe care proprietarul vrea sa se vada CLAR nu se pune acolo unde o vede doar cine
deruleaza pana la capitolul cinci.

CE REPARA PE DRUM, si e mai grav decat ce adauga. Toate cele cinci pagini de start scriau
«12 din 33 disponibile» in patru locuri (`meta description`, `og:description`, celula din
banda, banda din ultimul capitol) SI in datele structurate, in timp ce meniul ACELEIASI pagini
scria deja 7. Doua cifre diferite pe acelasi ecran, despre acelasi lucru. Toate se calculeaza
acum din `.engine/date/apartamente.json`, deci nu mai pot ramane in urma.

NICIO CIFRA IN PROZA. Cele trei numere stau in `custom properties` pe elementul blocului, iar
latimile barei se calculeaza din ele in CSS. Nimeni nu scrie procente de mana, si un pas care
nu atinge nicio fraza nu poate fi rupt nici de spatiul nedespartitor, nici de un backslash
intr-un sir de inlocuire.

    python3 pas_homepage.py --repo <cale>
    python3 pas_homepage.py --repo <cale> --apply
"""
import argparse
import io
import json
import os
import re

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALE_DATE = os.path.join(ENGINE, "date", "apartamente.json")

MARCA = "ilr-av"
NB = " "

PAGINI = [("ro", "index.html"), ("en", "en/index.html"), ("he", "he/index.html"),
          ("ar", "ar/index.html"), ("uk", "uk/index.html")]

# «12 din 33», «12 of 33», «12 מתוך 33», «12 من 33», «12 із 33». Un singur tipar pentru toate
# cinci: se schimba doar PRIMA cifra, totalul ramane exact cum e scris.
DIN = re.compile(r"(\d+)(\s*(?:din|of|de|מתוך|من|із)\s*)(\d+)")

SIRURI = {
    "ro": {"et_pl": "apartamente disponibile", "et_sg": "apartament disponibil",
           "lib": "libere", "rez": "rezervate", "vnd": "vândute",
           "scop": "din tot blocul"},
    "en": {"et_pl": "apartments available", "et_sg": "apartment available",
           "lib": "free", "rez": "reserved", "vnd": "sold",
           "scop": "of the whole building"},
    "he": {"et_pl": "דירות זמינות", "et_sg": "דירה זמינה",
           "lib": "פנויות", "rez": "שמורות", "vnd": "נמכרו",
           "scop": "מתוך כל הבניין"},
    "ar": {"et_pl": "شقق متاحة", "et_sg": "شقة متاحة",
           "lib": "متاحة", "rez": "محجوزة", "vnd": "مباعة",
           "scop": "من المبنى بأكمله"},
    "uk": {"et_pl": "квартири доступні", "et_sg": "квартира доступна",
           "lib": "вільні", "rez": "зарезервовані", "vnd": "продані",
           "scop": "з усього будинку"},
}

CSS = """
/* ===== ILR · DISPONIBILITATE SI GRAD DE OCUPARE, in banda copertei (21 aug 2026) =====
   Prefix .ilr-*, zero coliziuni. Zero JavaScript. Cele trei cifre stau in custom properties,
   latimile se calculeaza din ele: nimeni nu scrie procente de mana, deci nicio latime nu
   poate ramane in urma cand se mai vinde un apartament. */
#cov .cb{display:flex;flex-direction:column;justify-content:center}
#cov .cb-av{flex:2}
#cov .cb-av .v{font-size:clamp(2rem,2.6vw,2.7rem);line-height:.95;color:var(--ilr-verde)}
#cov .cb-av .l{margin-top:.5rem}
.ilr-av{--ilr-tot:calc(var(--ilr-lib) + var(--ilr-rez) + var(--ilr-vnd));
  --ilr-w-lib:calc(var(--ilr-lib) / var(--ilr-tot) * 100%);
  --ilr-w-rez:calc(var(--ilr-rez) / var(--ilr-tot) * 100%);
  --ilr-w-vnd:calc(var(--ilr-vnd) / var(--ilr-tot) * 100%);
  --ilr-verde:#5FC79E;--ilr-verde-rgb:95,199,158}
#cov .ilr-av{--ilr-verde:#5FC79E}
.ilr-bar{display:flex;height:9px;margin-top:.66rem;border-radius:999px;overflow:hidden;
  background:rgba(var(--bg-rgb),.62);box-shadow:inset 0 0 0 1px rgba(var(--cream-rgb),.18);
  transform:scaleX(0);transform-origin:left center;
  animation:ilrBar .9s cubic-bezier(.22,.6,.2,1) both;animation-delay:calc(var(--ed,0ms) + 420ms)}
html[dir="rtl"] .ilr-bar{transform-origin:right center}
.ilr-sg{flex:0 0 auto;height:100%;min-width:0}
.ilr-sg + .ilr-sg{border-inline-start:1px solid rgba(var(--bg-rgb),.7)}
.ilr-sg--vnd{flex-basis:var(--ilr-w-vnd);background:rgba(var(--cream-rgb),.24)}
.ilr-sg--rez{flex-basis:var(--ilr-w-rez);
  background:repeating-linear-gradient(135deg,rgba(var(--gold-rgb),.95) 0 3px,rgba(var(--gold-rgb),.24) 3px 7px)}
.ilr-sg--lib{flex-basis:var(--ilr-w-lib);
  background:linear-gradient(180deg,rgba(255,255,255,.2),rgba(255,255,255,0) 60%),var(--ilr-verde)}
html[dir="rtl"] .ilr-sg--rez{background-image:repeating-linear-gradient(45deg,rgba(var(--gold-rgb),.95) 0 3px,rgba(var(--gold-rgb),.24) 3px 7px)}
@keyframes ilrBar{from{transform:scaleX(0)}to{transform:scaleX(1)}}
/* Legenda merge in ORDINEA BAREI, stanga spre dreapta: vandut, rezervat, liber. Invers,
   ochiul face o traducere in plus la fiecare citire, si atunci legenda incurca in loc sa explice. */
.ilr-lg{display:flex;flex-wrap:wrap;justify-content:center;gap:.2rem .7rem;margin:.5rem 0 0;
  font-family:'Inter';font-size:.68rem;line-height:1.35;color:var(--cream-soft);white-space:nowrap}
.ilr-i{display:inline-flex;align-items:center;gap:.4em}
.ilr-i::before{content:"";flex:0 0 auto;width:.58em;height:.58em;border-radius:2px}
.ilr-i b{font-weight:600;color:var(--cream);font-variant-numeric:tabular-nums}
.ilr-i--lib::before{background:var(--ilr-verde)}
.ilr-i--lib b{color:var(--ilr-verde)}
.ilr-i--rez::before{background:repeating-linear-gradient(135deg,rgba(var(--gold-rgb),.95) 0 2px,rgba(var(--gold-rgb),.24) 2px 5px)}
html[dir="rtl"] .ilr-i--rez::before{background-image:repeating-linear-gradient(45deg,rgba(var(--gold-rgb),.95) 0 2px,rgba(var(--gold-rgb),.24) 2px 5px)}
.ilr-i--vnd::before{background:rgba(var(--cream-rgb),.24)}
.ilr-sc{margin-top:.28rem;font-family:'Inter';font-size:.66rem;line-height:1.3;
  color:var(--cream-soft);opacity:.72}
@media (min-width:761px) and (max-width:1040px){
  #cov .cb-av{flex:2.9}
  #cov .cb-av .v{font-size:2rem}
  .ilr-lg{font-size:.6rem;gap:.15rem .55rem}
  .ilr-sc{font-size:.6rem}
}
@media (min-width:761px) and (max-height:860px){
  #cov .cb{padding:.62rem .5rem .6rem}
  #cov .cb .v{font-size:1.34rem}
  #cov .cb-av .v{font-size:1.95rem}
  #cov .cb .l{font-size:.58rem;letter-spacing:.14em;margin-top:.4rem}
  .ilr-bar{margin-top:.48rem;height:8px}
  .ilr-lg{margin-top:.38rem;font-size:.62rem}
  .ilr-sc{margin-top:.2rem;font-size:.6rem}
}
/* Pe telefon banda e GRILA, nu flex: `flex:2` nu are niciun efect acolo, deci celula isi ia
   randul intreg prin `grid-column`. Fara asta, blocul ramanea inghesuit pe jumatate de rand. */
@media (max-width:760px){
  #cov .cb-av{grid-column:1 / -1}
  #cov .cb:last-child{grid-column:1 / -1}
  #cov .cb:nth-child(2n){border-left:0}
  #cov .cb:nth-child(2n+1):not(.cb-av){border-left:1px solid rgba(233,177,43,.16)}
  #cov .cb:nth-child(n+2){border-top:1px solid rgba(233,177,43,.16)}
  #cov .cb-av .v{font-size:1.9rem}
  .ilr-bar{height:10px;margin-top:.6rem}
  .ilr-lg{font-size:.7rem;gap:.2rem .8rem}
  .ilr-sc{font-size:.68rem}
}
@media (max-width:400px){.ilr-lg{flex-direction:column;align-items:center;gap:.12rem}}
@media (prefers-reduced-motion:reduce){.ilr-bar{animation:none;transform:none}}
"""


def numara(A):
    lib = sum(1 for a in A.values() if a["stare"] == "disponibil")
    rez = sum(1 for a in A.values() if a["stare"] == "rezervat")
    vnd = sum(1 for a in A.values() if a["stare"] == "vandut")
    return lib, rez, vnd


def bloc(lang, lib, rez, vnd):
    s = SIRURI[lang]
    eticheta = s["et_sg"] if lib == 1 else s["et_pl"]
    return (
        '<div class="cb cb-av %s" style="--ilr-lib:%d;--ilr-rez:%d;--ilr-vnd:%d">'
        '<div class="v">%d</div><div class="l">%s</div>'
        '<div class="ilr-bar" aria-hidden="true">'
        '<i class="ilr-sg ilr-sg--vnd"></i><i class="ilr-sg ilr-sg--rez"></i>'
        '<i class="ilr-sg ilr-sg--lib"></i></div>'
        '<div class="ilr-lg">'
        '<span class="ilr-i ilr-i--vnd"><b>%d</b> %s</span>'
        '<span class="ilr-i ilr-i--rez"><b>%d</b> %s</span>'
        '<span class="ilr-i ilr-i--lib"><b>%d</b> %s</span></div>'
        '<div class="ilr-sc">%s</div></div>'
        % (MARCA, lib, rez, vnd, lib, eticheta,
           vnd, s["vnd"], rez, s["rez"], lib, s["lib"], s["scop"]))


BLOC_VECHI = re.compile(r'<div class="cb cb-av ' + MARCA + r'".*?</div></div>', re.S)
CELULA_VECHE = re.compile(r'<div class="cb"><div class="v">\s*\d+\s*(?:din|of|מתוך|من|із)\s*'
                          r'\d+\s*</div><div class="l">[^<]*</div></div>')


def tinta(h):
    """Ce se inlocuieste: blocul pus de o rulare anterioara, DACA exista, altfel celula
    veche din banda.

    PRIMA VERSIUNE STERGEA INTAI SI CAUTA DUPA, si se distrugea singura: la a doua rulare
    isi scotea propriul bloc, apoi nu mai gasea celula veche (o inlocuise ea) si iesea fara
    sa puna nimic la loc. Banda ramanea cu o celula in minus, si nici macar nu se plangea,
    fiindca «nimic de facut» arata la fel cu «gata».
    A treia oara intr-o zi cand o garda scrisa gresit imbatraneste sau strica o pagina.
    Regula, si merita scrisa mare: nu sterge inainte sa stii ce pui in loc."""
    return BLOC_VECHI.search(h) or CELULA_VECHE.search(h)


CUVANT_LIBER = re.compile(r"(\d+)(\s+)(disponibile|disponibil|available|זמינות|متاحة|доступні)")
SEPARATOARE = ("din", "of", "מתוך", "من", "із")


def repara_cifrele(h, lib):
    """Toate cifrele de disponibilitate de pe pagina primesc valoarea de azi.

    DOUA TIPARE, fiindca textul nu e scris la fel peste tot:
      «12 din 33»                 -> se schimba doar prima cifra, totalul ramane
      «12 disponibile»            -> se schimba cifra
      «12 disponibile din 33»     -> primul tipar nu il prinde, al doilea da

    CAPCANA, si de asta a doua regula nu e un simplu `re.sub`: in «7 din 33 disponibile»,
    cifra lipita de cuvant e TOTALUL, nu numarul liberelor. Un tipar naiv ar fi rescris 33
    in 7 si ar fi stricat exact fraza pe care venise sa o repare. Deci se verifica ce sta
    inaintea cifrei si, daca e un separator de tipul «din», nu se atinge."""
    h = DIN.sub(lambda m: str(lib) + m.group(2) + m.group(3), h)

    def pe_cuvant(m):
        inainte = h[max(0, m.start() - 14):m.start()]
        if any(s in inainte for s in SEPARATOARE):
            return m.group(0)
        return str(lib) + m.group(2) + m.group(3)

    return CUVANT_LIBER.sub(pe_cuvant, h)


def proceseaza(h, lang, lib, rez, vnd):
    schimbat = False
    m = tinta(h)
    if not m:
        return h, False
    nou_bloc = bloc(lang, lib, rez, vnd)
    if h[m.start():m.end()] != nou_bloc:
        h = h[:m.start()] + nou_bloc + h[m.end():]
        schimbat = True

    nou = repara_cifrele(h, lib)
    if nou != h:
        h, schimbat = nou, True

    # Datele structurate: aceeasi cifra, acelasi loc de adevar. Tiparul accepta spatii
    # oriunde: JSON-LD-ul de pe pagina asta e scris cu spatii dupa doua puncte, iar prima
    # versiune, scrisa fara ele, nu a prins nimic si a iesit tacut.
    nou = re.sub(r'("numberOfAvailableAccommodationUnits"\s*:\s*\{[^}]*?"value"\s*:\s*)"?\d+"?',
                 lambda x: x.group(1) + str(lib), h)
    if nou != h:
        h, schimbat = nou, True

    if "ILR · DISPONIBILITATE" not in h:
        i = h.rfind("</style>")
        if i > 0:
            h = h[:i] + CSS + h[i:]
            schimbat = True
    return h, schimbat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    A = json.load(io.open(CALE_DATE, encoding="utf-8"))["apartamente"]
    lib, rez, vnd = numara(A)

    atinse = []
    for lang, rel in PAGINI:
        fp = os.path.join(a.repo, rel)
        if not os.path.exists(fp):
            continue
        h = io.open(fp, encoding="utf-8").read()
        nou, schimbat = proceseaza(h, lang, lib, rez, vnd)
        if schimbat and nou != h:
            atinse.append(lang)
            if a.apply:
                io.open(fp, "w", encoding="utf-8", newline="\n").write(nou)

    print("pas_homepage: %d libere · %d rezervate · %d vandute · %d in tot"
          % (lib, rez, vnd, lib + rez + vnd))
    print("              pagini atinse: %s  (%s)"
          % (", ".join(atinse) if atinse else "niciuna",
             "APLICAT" if a.apply else "PROBA"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
