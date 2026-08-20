#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LISTA DE APARTAMENTE de pe /apartamente/: tot blocul, nu doar ce e de vanzare.

CERUT DE OBREA, prin Andy, 20 aug 2026:
  1. sa se vada si apartamentele vandute, dar FARA pagina individuala
  2. rezervatele, cu eticheta clara
  3. disponibilele, evidentiate printr-o culoare distincta sau o eticheta estetica
  4. taburi pe numarul de camere
  5. un comutator "doar disponibilele"

DE CE SE ARATA SI CELE VANDUTE, desi nu se mai pot cumpara. Un bloc din care s-au vandut 18 din
31 spune singur ca merge bine. Lista scurta de 13 nu spune nimic; lista intreaga, cu 18 taiate,
spune ca ai ramas cu ce a mai ramas si ca nu mai e mult. E acelasi fapt, citit altfel, si e
argumentul cel mai onest pe care il avem: nu e o afirmatie despre noi, e o numaratoare.

Cele vandute NU primesc pagina proprie si NU primesc pret: nu au ce sa vanda si nu au ce sa
indexeze. Sunt `<div>`, nu `<a>`, deci nici nu se poate da click pe ele.

SURSA e `.engine/date/apartamente.json`, toate cele 31. Aici nu se scrie niciun pret si nicio
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

CSS = '<link rel="stylesheet" href="/assets/stare-v1.css">'
ANCORA_CSS = '<link rel="stylesheet" href="/assets/pagini-v33.css">'

NB = " "

# ordinea de afisare: de sus in jos, cum se urca in bloc
NIVELE = [("etaj 7", "Etajul 7"), ("etaj 6", "Etajul 6"), ("etaj 5", "Etajul 5"),
          ("etaj 4", "Etajul 4"), ("etaj 3", "Etajul 3"), ("etaj 2", "Etajul 2"),
          ("etaj 1", "Etajul 1"), ("parter", "Parter")]

# coada editoriala pastrata din pagina veche, ca sa nu se piarda ce era scris de om
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
    """Un card. Cu adresa daca are pagina, altfel o cutie moarta: vandutul nu se da la click."""
    cam = a["camere"]
    stare = a["stare"]
    eticheta = {"disponibil": "Disponibil", "rezervat": "Rezervat", "vandut": "Vândut"}[stare]
    ins = '<span class="stare stare-%s">%s</span>' % (stare, eticheta)
    titlu = "Apartament %d camere · %s" % (cam, et)
    mic = "<small>ap.%s%s</small>" % (NB, nr)

    randuri = ['<h3>%s%s%s%s</h3>' % (titlu, NB, mic, ins)]
    if a.get("total"):
        randuri.append('<p class="cm"><b>%s mp în%stotal</b> · compartimentare%smodulară</p>'
                       % (a["total"], NB, NB))
    if stare != "vandut" and a.get("pret"):
        p = '<p class="cp">%s EUR + TVA %s%%' % (a["pret"], a.get("tva", "21"))
        if a.get("pret_total"):
            p += "<small>(%s EUR total)</small>" % a["pret_total"]
        randuri.append(p + "</p>")

    date = ' data-cam="%d" data-stare="%s"' % (cam, stare)
    if stare != "vandut" and a.get("href"):
        randuri.append('<span class="cl">Vedeți detalii</span>')
        return ('<a class="card rv e-%s" data-fx="pop"%s href="%s">%s</a>'
                % (stare, date, a["href"], "".join(randuri)))
    clasa = "card rv card-mut" + ("" if stare == "vandut" else " e-" + stare)
    return '<div class="%s"%s>%s</div>' % (clasa, date, "".join(randuri))


def bara(A):
    lib = numara(A, stare="disponibil")
    rez = numara(A, stare="rezervat")
    vnd = numara(A, stare="vandut")
    return (
        '<div class="filtre rv" data-fx="rise" id="filtre">'
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
    out = [bara(A), '<div class="lista-ap" id="lista-ap">']
    for cheie, titlu in NIVELE:
        nr_et = [k for k, v in A.items() if v["etaj"] == cheie]
        if not nr_et:
            continue
        nr_et.sort(key=int)
        lib = sum(1 for k in nr_et if A[k]["stare"] == "disponibil")
        et_scurt = titlu.replace("Etajul ", "Etaj ")
        out.append('<section class="etaj-ap" data-etaj="%s">' % cheie)
        out.append('<h2 class="rv" data-fx="slide">%s · %s%s</h2>'
                   % (titlu, cuvant(lib), COADA.get(cheie, "")))
        out.append('<div class="grid">')
        out.extend(card(k, A[k], et_scurt if cheie != "parter" else "Parter") for k in nr_et)
        out.append("</div></section>")
    out.append("</div>")
    return "\n".join(out)


JS = """<script>
(function(){
  var lista=document.getElementById('lista-ap');
  if(!lista)return;
  var taburi=[].slice.call(document.querySelectorAll('.ft'));
  var doarLibere=document.getElementById('f-libere');
  function aplica(){
    var cam=lista.getAttribute('data-f-cam')||'toate';
    var lib=lista.getAttribute('data-f-lib')==='1';
    var vazute=0;
    [].forEach.call(lista.querySelectorAll('.card'),function(c){
      var ok=(cam==='toate'||c.getAttribute('data-cam')===cam)
          && (!lib||c.getAttribute('data-stare')==='disponibil');
      c.hidden=!ok; if(ok)vazute++;
    });
    [].forEach.call(lista.querySelectorAll('.etaj-ap'),function(s){
      s.hidden=!s.querySelector('.card:not([hidden])');
    });
    var gol=document.getElementById('f-gol');
    if(gol)gol.hidden=vazute>0;
  }
  taburi.forEach(function(b){
    b.addEventListener('click',function(){
      taburi.forEach(function(x){x.classList.remove('on');x.setAttribute('aria-pressed','false')});
      b.classList.add('on'); b.setAttribute('aria-pressed','true');
      lista.setAttribute('data-f-cam',b.getAttribute('data-cam')); aplica();
    });
  });
  if(doarLibere)doarLibere.addEventListener('change',function(){
    lista.setAttribute('data-f-lib',doarLibere.checked?'1':'0'); aplica();
  });
})();
</script>"""

GOL = ('<p class="f-gol" id="f-gol" hidden>Nu e niciun apartament care să '
       'bifeze filtrele alese. Scoateți un filtru și reapare lista.</p>')


H2 = re.compile(r'<h2 class="rv" data-fx="slide">([^<]*)')
E_NIVEL = re.compile(r"^(Etajul \d|Parter)\b")


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
    if '<div class="grid">' not in zona and '<div class="lista-ap"' not in zona:
        return html, False

    nou = lista(A) + "\n" + GOL + "\n"
    return html[:inceput] + nou + html[sfarsit:], True


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
    if CSS not in nou:
        nou = nou.replace(ANCORA_CSS, ANCORA_CSS + "\n" + CSS, 1)
    if 'id="lista-ap"' in nou and "getElementById('lista-ap')" not in nou:
        nou = nou.replace("</body>", JS + "\n</body>", 1)

    if a.apply and nou != html:
        io.open(fp, "w", encoding="utf-8", newline="\n").write(nou)
    print("pas_lista: %d carduri (%d libere, %d rezervate, %d vandute), "
          "%d preturi recuperate  (%s)"
          % (len(A), numara(A, stare="disponibil"), numara(A, stare="rezervat"),
             numara(A, stare="vandut"), n, "APLICAT" if a.apply else "PROBA"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
