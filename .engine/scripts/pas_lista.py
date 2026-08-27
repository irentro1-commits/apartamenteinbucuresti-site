#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LISTA DE APARTAMENTE de pe /apartamente/: tot blocul, nu doar ce e de vanzare.

CERUT DE OBREA, prin Andy, 20 aug 2026:
  1. sa se vada si apartamentele vandute, dar FARA pagina individuala
  2. rezervatele, cu eticheta clara
  3. disponibilele, evidentiate printr-o culoare distincta sau o eticheta estetica
  4. taburi pe numarul de camere
  5. un comutator "doar disponibilele"

DE CE SE ARATA SI CELE VANDUTE, desi nu se mai pot cumpara. Un bloc din care s-au vandut 19 din
35 spune singur ca merge bine. Lista scurta de 9 nu spune nimic; lista intreaga, cu 19 taiate,
spune ca ai ramas cu ce a mai ramas si ca nu mai e mult. E acelasi fapt, citit altfel, si e
argumentul cel mai onest pe care il avem: nu e o afirmatie despre noi, e o numaratoare.

Cele vandute NU primesc pagina proprie si NU primesc pret: nu au ce sa vanda si nu au ce sa
indexeze. Sunt `<div>`, nu `<a>`, deci nici nu se poate da click pe ele.

SURSA e `.engine/date/apartamente.json`, toate cele 35: 3 la parter si cate 4 pe fiecare
din cele 8 etaje. Penthouse-urile de la etajul 8 au fost scoase din plan (Andy, 26 aug 2026). Aici nu se scrie niciun pret si nicio
stare: se citesc de acolo. Preturile care lipsesc din date se recupereaza o singura data din
cardurile existente si se scriu inapoi in date, ca sa nu ramana niciodata in doua locuri.

Filtrarea merge FARA JavaScript in sensul care conteaza: fara el se vad toate, ceea ce e
raspunsul corect. Cu el, se filtreaza pe loc, fara sa se reincarce pagina.

    python3 pas_lista.py --repo <cale>            # proba
    python3 pas_lista.py --repo <cale> --apply
"""
import argparse
import io
import json
import os
import re

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALE_DATE = os.path.join(ENGINE, "date", "apartamente.json")

# Doua foi, si amandoua trebuie sa fie acolo: insignele de stare traiesc in stare-v3.css,
# randurile in carduri-v5.css. Injectarea uneia singure lasa etichetele nestilizate.
CSS = ('<link rel="stylesheet" href="/assets/stare-v3.css">' + "\n" +
       '<link rel="stylesheet" href="/assets/carduri-v5.css">')
ANCORA_CSS = '<link rel="stylesheet" href="/assets/pagini-v34.css">'

NB = " "

# PLANSELE MICI, citite din manifestul lor. `/planuri/*` se serveste `immutable` un an,
# deci fisierele poarta versiune in nume, iar versiunea are UN SINGUR loc: manifestul
# scris de `_fise/build_mini.py`. Aici nu se compune niciodata un nume de fisier cu mana:
# asa s-a nascut lista cu sase poze la sapte apartamente disponibile.
_MANIFEST = os.path.join(os.path.dirname(ENGINE), "planuri", "mini", "index.json")
PLANSE = (json.load(io.open(_MANIFEST, encoding="utf-8"))
          if os.path.exists(_MANIFEST) else {})

# ordinea de afisare: de sus in jos, cum se urca in bloc
NIVELE = [("etaj 8", "Etajul 8"), ("etaj 7", "Etajul 7"), ("etaj 6", "Etajul 6"),
          ("etaj 5", "Etajul 5"),
          ("etaj 4", "Etajul 4"), ("etaj 3", "Etajul 3"), ("etaj 2", "Etajul 2"),
          ("etaj 1", "Etajul 1"), ("parter", "Parter")]

# coada editoriala pastrata din pagina veche, ca sa nu se piarda ce era scris de om
# Cratima din "penthouse-uri" e NEDESPARTITOARE (U+2011): arata identic, dar browserul
# nu mai poate rupe randul in ea. Cu cratima obisnuita, titlul se taia in "penthouse-"
# si "uri" pe randul urmator, si asta se vedea din prima.
COADA = {"etaj 7": " · priveliștea cea mai deschisă"}


def incarca():
    return json.load(io.open(CALE_DATE, encoding="utf-8"))


def salveaza(d):
    io.open(CALE_DATE, "w", encoding="utf-8", newline="\n").write(
        json.dumps(d, ensure_ascii=False, indent=2) + "\n")


def recupereaza_preturi(d, html):
    """Preturile stau azi in cardurile deja scrise. Se iau o data si se muta in date, ca de
    acolo incolo sa existe intr-un singur loc."""
    A = d["apartamente"]
    tipar = re.compile(
        r'<a class="card[^"]*"[^>]*href="(/apartamente/[^"]+)"(.*?)</a>', re.S)
    # SPATIILE POT FI NEDESPARTITOARE. `pas_asezare` leaga ultimele doua cuvinte ale fiecarui
    # bloc, deci in card scrie "EUR total", nu "EUR total". Un tipar cu spatiu obisnuit
    # nu prinde nimic si iese tacut cu zero preturi recuperate. A doua oara in aceeasi zi.
    S = r"[\s ]"
    pret = re.compile(r'class="cp">([\d.]+)' + S + r"EUR" + S + r"\+" + S + r"TVA" + S +
                      r"(\d+)%<small>\(([\d.]+)" + S + r"EUR" + S + r"total\)")
    mp = re.compile(r"<b>([\d,]+)" + S + r"mp")
    n = 0
    for m in tipar.finditer(html):
        href, corp = m.group(1), m.group(2)
        nr = re.search(r"-ap-(\d+)/", href)
        if not nr or nr.group(1) not in A:
            continue
        a = A[nr.group(1)]
        a["href"] = href
        g = mp.search(corp)
        if g:
            a["total"] = g.group(1)
        g = pret.search(corp)
        if g:
            a["pret"], a["tva"], a["pret_total"] = g.group(1), g.group(2), g.group(3)
            n += 1
    return n


def numara(A, **f):
    n = 0
    for a in A.values():
        if all(a.get(k) == v for k, v in f.items()):
            n += 1
    return n


def cuvant(n):
    if n == 0:
        return "niciunul" + NB + "liber"
    return "%d%s%s" % (n, NB, "disponibil" if n == 1 else "disponibile")


def card(nr, a, et):
    """Un RAND, nu un card.

    Andy, 21 aug 2026: intai *"fa-le pe toate mici si pune-le 2x2"*, apoi, imediat,
    *"sau in linie de fapt mai degraba"*. A doua varianta e si cea corecta, si se poate
    argumenta: cumparatorul nu citeste un apartament, ci COMPARA mai multe. Pe randuri,
    preturile cad unul sub altul intr-o singura coloana si ochiul le parcurge pe verticala
    fara sa sara. Intr-o grila 2x2, aceleasi preturi sunt imprastiate pe doua axe si fiecare
    comparatie cere o miscare de ochi in plus.

    Toate cele trei stari au EXACT aceleasi celule, deci toate randurile au aceeasi inaltime.
    Vandutul are coloana de pret goala: nu se inventeaza un pret ca sa iasa simetria, si nu
    devine clicabil ce nu se poate cumpara.
    """
    cam = a["camere"]
    stare = a["stare"]
    eticheta = {"disponibil": "Disponibil", "rezervat": "Rezervat", "vandut": "Vândut"}[stare]
    ins = '<span class="stare stare-%s">%s</span>' % (stare, eticheta)

    # Insigna sta INAUNTRUL celulei cu numarul. Lasata afara, devenea a cincea celula a
    # grilei si impingea toate coloanele cu una: pretul ajungea in coloana a treia, iar
    # marginile nu se mai aliniau intre randuri. Masurat, nu banuit.
    # PLANSA APARTAMENTULUI. Andy, 21 aug 2026, aratand lista concurentului: "pune ca florin
    # dar sa avem astea pe chestia noastra smechera", apoi "trebuie pozele mult mai mari sa
    # isi dea oamenii seama" si "sa nu para ca l-am copiat pe asta, sa avem propria noastra
    # identitate". La el e o poza decupata sa umple o cutie. Aici e o PLANSA: randarea intreaga,
    # asezata pe hartie crem, in aceeasi conventie ca fisa de apartament. Se genereaza in
    # `_fise/build_mini.py`, nu se decupeaza aici.
    # POZA DOAR PE DISPONIBILE. Andy, tot 21 aug: "nu le punem pe alea rezervate cu poza".
    # Are dreptate si e si design bun: lista da greutate vizuala fix la ce se poate cumpara.
    # Un plan mare langa un apartament pe care nu il poti lua nu ajuta pe nimeni, doar
    # imparte atentia. Rezervatele si vandutele raman randuri scurte, fara celula de plansa.
    cale = PLANSE.get(nr)
    if stare == "disponibil" and cale:
        foto = ('<span class="ap-foto"><img src="%s" alt="Plan apartament %s" '
                'width="864" height="640" loading="lazy" decoding="async"></span>'
                % (cale, nr))
    else:
        foto = ""     # fara celula deloc: randul are patru coloane, nu cinci

    celule = [
        '<span class="ap-nr">ap.%s%s%s</span>' % (NB, nr, ins),
        '<span class="ap-d">%s · %s</span>' % (
            "Penthouse" if a.get("tip") == "penthouse"
            else ("%d camere" % cam) if cam else "Apartament", et),
        '<span class="ap-mp">%s</span>' % (
            (a["total"] + NB + "mp") if a.get("total") else "&mdash;"),
    ]

    if stare != "vandut" and a.get("pret"):
        pret = '<b>%s</b><i>EUR + TVA %s%%</i>' % (a["pret"], a.get("tva", "21"))
        if a.get("pret_total"):
            pret += '<em>%s EUR%stotal</em>' % (a["pret_total"], NB)
        celule.append('<span class="ap-p">%s</span>' % pret)
    else:
        celule.append('<span class="ap-p ap-p-gol" aria-hidden="true"></span>')

    if foto:
        celule.insert(0, foto)
    date = ((' data-cam="%d"' % cam if cam else "") + ' data-stare="%s"' % stare
            + (' data-foto' if foto else ""))
    corp = "".join(celule)
    if stare != "vandut" and a.get("href"):
        # FARA `rv` si fara `data-fx` pe rand. Randul nu se anima individual din doua motive:
        # treizeci si unu de randuri care apar unul cate unul e zgomot, nu miscare; si, cat
        # timp nu s-au revelat, au un `transform` pe ele, deci se masoara altfel decat arata.
        # Sectiunea etajului pastreaza revelarea, deci lista tot intra frumos in pagina.
        return ('<a class="aprow e-%s"%s href="%s">%s</a>'
                % (stare, date, a["href"], corp))
    clasa = "aprow aprow-mut" + ("" if stare == "vandut" else " e-" + stare)
    return '<div class="%s"%s>%s</div>' % (clasa, date, corp)


def bara(A):
    lib = numara(A, stare="disponibil")
    rez = numara(A, stare="rezervat")
    vnd = numara(A, stare="vandut")
    return (
        '<div class="filtre rv" data-fx="rise" id="filtre" data-filtre-pentru="lista-ap">'
        '<div class="f-tabs" role="group" aria-label="Filtrează după numărul de camere">'
        '<button type="button" class="ft on" data-cam="toate" aria-pressed="true">Toate</button>'
        '<button type="button" class="ft" data-cam="2" aria-pressed="false">2 camere</button>'
        '<button type="button" class="ft" data-cam="3" aria-pressed="false">3 camere</button>'
        "</div>"
        '<label class="f-sw"><input type="checkbox" id="f-libere">'
        '<span class="f-sw-b" aria-hidden="true"></span>'
        "<span>Doar disponibile</span></label>"
        '<p class="f-num" id="f-num" role="status">'
        "<b>%d</b> disponibile · %d rezervate · %d vândute, din %d în%stot</p>"
        "</div>" % (lib, rez, vnd, lib + rez + vnd, NB))


def lista(A):
    out = [bara(A), '<div class="lista-ap" id="lista-ap" data-filtrabil>']
    for cheie, titlu in NIVELE:
        nr_et = [k for k, v in A.items() if v["etaj"] == cheie]
        if not nr_et:
            continue
        nr_et.sort(key=int)
        lib = sum(1 for k in nr_et if A[k]["stare"] == "disponibil")
        et_scurt = titlu.replace("Etajul ", "Etaj ")
        out.append('<section class="etaj-ap" data-sectiune data-etaj="%s">' % cheie)
        # Pana pe 26 aug 2026 etajul 8 sarea numaratoarea, fiindca era etajul celor doua
        # penthouse-uri vandute si "niciunul liber" ar fi spus acelasi lucru de doua ori.
        # Andy, 26 aug 2026: *"BLOCU LVA FI P+8 FARA PENTHOUSEURI- SUNT SOCASE IDN PLAN"*.
        # Etajul 8 are patru apartamente ca oricare altul, deci se numara ca oricare altul.
        if False:
            pass
        else:
            out.append('<h2 class="rv" data-fx="slide">%s · %s%s</h2>'
                       % (titlu, cuvant(lib), COADA.get(cheie, "")))
        out.append('<div class="aplist">')
        out.extend(card(k, A[k], et_scurt if cheie != "parter" else "Parter") for k in nr_et)
        out.append("</div></section>")
    out.append("</div>")
    return "\n".join(out)


JS = '<script src="/assets/filtre-v2.js" defer></script>'

GOL = ('<p class="f-gol" id="f-gol" hidden>Nu e niciun apartament care să '
       'bifeze filtrele alese. Scoateți un filtru și reapare lista.</p>')


H2 = re.compile(r'<h2 class="rv" data-fx="slide">([^<]*)')
E_NIVEL = re.compile(r"^(Etajul \d|Parter)\b")

# blocul de filtrare scris INLINE de versiunile vechi ale acestui pas
INLINE_VECHI = re.compile(r"<script>\s*\(function\(\)\{\s*var lista=document\.getElementById"
                          r"\('lista-ap'\).*?</script>\s*", re.S)


def leaga_filtrul(h):
    """Scoate orice bloc de filtrare scris inline de o versiune veche a pasului, si pune
    trimiterea catre fisierul de azi.

    DE CE, si e defectul care a ajuns pe LIVE pe 21 aug 2026: blocul era injectat inline si
    sarit daca pagina avea deja unul. Cand randurile s-au redenumit din `.card` in `.aprow`,
    pagina a ramas cu scriptul vechi, care cauta elemente disparute. Comutatorul "doar
    disponibile" ascundea TOT si scria "nu e niciun apartament", desi erau sapte.
    Un cod injectat care nu se poate INLOCUI e un cod care imbatraneste in pagina."""
    h = INLINE_VECHI.sub("", h)
    if JS not in h:
        h = h.replace("</body>", JS + "\n</body>", 1)
    return h


def rescrie(html, A):
    """Inlocuieste zona de lista, si numai pe ea.

    Ancora de INCEPUT: primul titlu de nivel, sau bara de filtre daca pasul a mai rulat.
    Ancora de SFARSIT: primul titlu care NU mai e de nivel ("Direct de la dezvoltator").
    Nu se cauta ultimul `</div>`: pe pagina asta ultimul `</div>` e in subsol, iar o ancora
    gresita ar fi mancat jumatate de pagina fara sa dea nicio eroare."""
    filtre = html.find('<div class="filtre')
    titluri = [(m.start(), m.group(1)) for m in H2.finditer(html)]
    niveluri = [p for p, t in titluri if E_NIVEL.match(t.strip())]
    if not niveluri:
        return html, False
    inceput = min(filtre, niveluri[0]) if filtre >= 0 else niveluri[0]
    dupa = [p for p, t in titluri if p > niveluri[-1] and not E_NIVEL.match(t.strip())]
    if not dupa:
        return html, False
    sfarsit = dupa[0]

    # paragraful "nu bifeaza filtrele" si sectiunile vechi raman in afara zonei taiate
    zona = html[inceput:sfarsit]
    if '<div class="aplist">' not in zona and '<div class="lista-ap"' not in zona:
        return html, False

    nou = lista(A) + "\n" + GOL + "\n"
    return html[:inceput] + nou + html[sfarsit:], True


PROW = re.compile(r'<a class="prow([^"]*)"([^>]*?)href="(/apartamente/[^"]+)"')
H2_CAMERE = re.compile(r'<h2 class="rv" data-fx="slide">(\d camere ·[^<]*)</h2>')


def capat_bloc(h, start, eticheta="div"):
    """Capatul unui element, numarand deschiderile si inchiderile. Nu se cauta primul
    `</div>`: containerul are copii, si o ancora gresita taie pagina in doua."""
    adanc = 0
    for m in re.finditer(r"<%s\b|</%s>" % (eticheta, eticheta), h[start:]):
        adanc += 1 if m.group(0).startswith("</") is False else -1
        if adanc == 0:
            return start + m.end()
    return -1


def bara_pret(rand_stari):
    """Bara pentru /preturi/. Numara ce e PE PAGINA, nu tot blocul: acolo nu apar cele
    vandute, iar o bara care ar spune 31 langa o lista de 12 ar fi o contradictie."""
    lib = sum(1 for s in rand_stari if s == "disponibil")
    rez = sum(1 for s in rand_stari if s == "rezervat")
    return (
        '<div class="filtre rv" data-fx="rise" data-filtre-pentru="lista-pret">'
        '<div class="f-tabs" role="group" aria-label="Filtrează după numărul de camere">'
        '<button type="button" class="ft on" data-cam="toate" aria-pressed="true">Toate</button>'
        '<button type="button" class="ft" data-cam="2" aria-pressed="false">2 camere</button>'
        '<button type="button" class="ft" data-cam="3" aria-pressed="false">3 camere</button>'
        "</div>"
        '<label class="f-sw"><input type="checkbox" id="f-libere-pret">'
        '<span class="f-sw-b" aria-hidden="true"></span>'
        "<span>Doar disponibile</span></label>"
        '<p class="f-num" role="status"><b>%d</b> disponibile · %d rezervate, '
        "din %d în%stot</p></div>" % (lib, rez, lib + rez, NB))


def rescrie_preturi(html, A):
    """Aceleasi filtre pe /preturi/. Randurile de acolo nu se regenereaza, doar primesc
    atributele dupa care stie filtrul sa lucreze, iar sectiunile se inchid intr-un container.

    CONTORUL SE REIMPROSPATEAZA SI CAND FILTRUL E DEJA ACOLO. Pana pe 27 aug 2026, functia
    iesea din prima linie daca gasea `lista-pret`, deci cifrele scrise la prima inserare
    ramaneau acolo pentru totdeauna. Pe 27 aug pagina inca spunea "7 disponibile, 5
    rezervate, din 12 in tot" dupa ce blocul avea 9 libere, 7 rezervate si 16 randuri.
    Nimeni nu scria cifra aia a doua oara, fiindca nimeni nu se intreba daca s-a schimbat.
    """
    if "lista-pret" in html:
        lib = sum(1 for v in A.values() if v["stare"] == "disponibil")
        rez = sum(1 for v in A.values() if v["stare"] == "rezervat")
        # "din N in tot" numara randurile de pe PAGINA, adica ce se poate cumpara,
        # nu tot blocul: vandutele nu au rand aici.
        pe_pagina = len(re.findall(r'<a class="prow', html))
        nou_contor = ('<p class="f-num" role="status"><b>%d</b> disponibile · '
                      '%d rezervate, din %d în%stot</p>' % (lib, rez, pe_pagina, NB))
        html2 = re.sub(r'<p class="f-num"[^>]*>.*?</p>', nou_contor, html, count=1,
                       flags=re.S)
        return html2, False, 0

    stari = []

    def pe_prow(m):
        nr = re.search(r"-ap-(\d+)/", m.group(3))
        a = A.get(nr.group(1)) if nr else None
        if not a:
            return m.group(0)
        stari.append(a["stare"])
        return ('<a class="prow%s"%sdata-cam="%d" data-stare="%s" href="%s"'
                % (m.group(1), m.group(2), a["camere"], a["stare"], m.group(3)))

    html = PROW.sub(pe_prow, html)
    if not stari:
        return html, False, 0

    # fiecare pereche titlu + lista devine o sectiune, ca sa dispara cu titlu cu tot
    bucati, pozitii = [], [m.start() for m in H2_CAMERE.finditer(html)]
    if not pozitii:
        return html, False, 0
    ultim = 0
    for p in pozitii:
        inc_lista = html.find('<div class="plist"', p)
        if inc_lista < 0:
            continue
        sf = capat_bloc(html, inc_lista)
        if sf < 0:
            continue
        bucati.append(html[ultim:p])
        bucati.append('<section data-sectiune>' + html[p:sf] + "</section>")
        ultim = sf
    bucati.append(html[ultim:])
    html = "".join(bucati)

    # containerul se inchide in jurul tuturor sectiunilor, o data
    prima = html.find("<section data-sectiune>")
    ultima = html.rfind("</section>") + len("</section>")
    gol = ('<p class="f-gol" id="lista-pret-gol" hidden>Nu e niciun apartament care să '
           'bifeze filtrele alese. Scoateți un filtru și reapare lista.</p>')
    html = (html[:prima] + bara_pret(stari) +
            '<div id="lista-pret" data-filtrabil>' + html[prima:ultima] + "</div>" +
            gol + html[ultima:])
    return html, True, len(stari)


NOTA_PH = "nota-penthouse"


def nota_penthouse(h, A):
    """Pe /preturi/ se vad doar cele care se mai pot cumpara, dar totalul scris peste tot pe
    sit e 33. Fara o propozitie care sa inchida diferenta, cititorul aduna singur si nu-i iese.
    Andy, 21 aug 2026: *"pune peste tot clar 2 penthouse-uri deja vandute- in total 33"*."""
    # SE INLOCUIESTE, nu se sare. O garda de tip "exista deja ceva" lasa in pagina versiunea
    # veche a textului cand textul se schimba, si exact asta s-a intamplat acum o ora cu blocul
    # de filtrare. Garda corecta e "exista exact ce pun eu acum", iar cel mai simplu mod de a o
    # respecta e sa stergi si sa scrii din nou.
    h = re.sub(r'<p class="' + NOTA_PH + r'">.*?</p>', "", h, flags=re.S)
    ph = [k for k, v in A.items() if v.get("tip") == "penthouse"]
    de_vanzare = sum(1 for v in A.values() if v["stare"] != "vandut")
    if not ph:
        return h
    # FARA cifra pentru "cele care se mai pot cumpara": pe /preturi/ apar 12 randuri, dar in
    # date sunt 13 nevandute, fiindca ap. 18 a intrat si a iesit din oferta intr-o zi si nu are
    # rand aici. O cifra care nu se potriveste cu ce numeri pe ecran strica exact increderea
    # pe care o construieste nota.
    nota = ('<p class="%s">Blocul are %d de apartamente în total, dintre care %d '
            'penthouse‑uri la ultimul etaj, vândute de la început. Aici sunt cele care se '
            'mai pot cumpăra; lista întreagă, etaj cu etaj, este pe '
            '<a href="/apartamente/">pagina de apartamente</a>.</p>'
            % (NOTA_PH, len(A), len(ph)))
    i = h.find('<div id="lista-pret"')
    if i < 0:
        return h
    return h[:i] + nota + h[i:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    fp = os.path.join(a.repo, "apartamente", "index.html")
    html = io.open(fp, encoding="utf-8").read()
    d = incarca()
    n = recupereaza_preturi(d, html)
    if n and a.apply:
        salveaza(d)
    A = d["apartamente"]

    nou, ok = rescrie(html, A)
    if not ok:
        print("pas_lista: nu am gasit ancora, nu ating nimic")
        return 1
    # Fiecare foaie se verifica SEPARAT. Verificarea pe sirul concatenat trecea si atunci cand
    # una din ele era deja in pagina, si o adauga a doua oara: pagina ajunsese cu stare-v3.css
    # legat de doua ori.
    for foaie in CSS.split("\n"):
        if foaie and foaie not in nou:
            nou = nou.replace(ANCORA_CSS, ANCORA_CSS + "\n" + foaie, 1)
    nou = leaga_filtrul(nou)

    if a.apply and nou != html:
        io.open(fp, "w", encoding="utf-8", newline="\n").write(nou)
    print("pas_lista: %d randuri (%d libere, %d rezervate, %d vandute), "
          "%d preturi recuperate  (%s)"
          % (len(A), numara(A, stare="disponibil"), numara(A, stare="rezervat"),
             numara(A, stare="vandut"), n, "APLICAT" if a.apply else "PROBA"))

    # --- aceleasi filtre pe pagina de preturi ---
    fp2 = os.path.join(a.repo, "preturi", "index.html")
    if os.path.exists(fp2):
        h2 = io.open(fp2, encoding="utf-8").read()
        n2, pus, cate = h2, False, 0
        n2, pus, cate = rescrie_preturi(h2, A)
        for foaie in CSS.split("\n"):
            if foaie and foaie not in n2:
                n2 = n2.replace(ANCORA_CSS, ANCORA_CSS + "\n" + foaie, 1)
        n2 = nota_penthouse(n2, A)
        n2 = leaga_filtrul(n2)
        if a.apply and n2 != h2:
            io.open(fp2, "w", encoding="utf-8", newline="\n").write(n2)
        print("            /preturi/: %s, %d randuri marcate"
              % ("filtre puse" if pus else "filtre deja acolo", cate))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
