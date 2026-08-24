#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""INSIGNA LIVE: ceas la ora Romaniei, in pagina, care merge singur.

Andy, 21 aug 2026: *"pune si badge live acolo la apartamente si cu ora exacta, sa stie lumea
ca asta e disponibilitatea lor acum si la data asta, verificat cu dezvoltatorul live gen"*.

Andy, 24 aug 2026, verbatim, dupa ce a vazut insigna inghetata la 21 august: *"Disponibilitate
verificată cu dezvoltatorul 21 august, ora 06:29 ba fa cehstia asta sa fei Live Live coaie-
gen la ora si data acutala leaga ceva un ceas la ora roamniei si asta e gen nu la 21 august
plm peste tot unde e asa"*.

CE S-A SCHIMBAT, SI CE AM SPUS INAINTE SA SCHIMB. Pana pe 24 aug, insigna arata `_verificat.moment`
din `.engine/date/apartamente.json`, adica ora la care cineva chiar a intrebat dezvoltatorul, si
se stingea dupa 48 de ore. Motivul scris atunci: un ceas luat la build ar face situl sa spuna
vesnic "verificat acum cinci minute". Obiectia i-a fost spusa lui Andy pe 24 aug si a decis
ceasul viu. Textul ramane cum e; **daca vrea si adevarul propozitiei, se schimba un cuvant**:
"Disponibilitate verificată cu dezvoltatorul" -> "Prețuri și disponibilitate, la zi:". Atunci
ceasul arata ACTUALIZAREA, nu o convorbire care nu a avut loc.

CUM MERGE. Ceasul e in pagina, nu la build: `Intl.DateTimeFormat` cu `timeZone: "Europe/Bucharest"`,
deci arata ora Romaniei indiferent de unde se uita omul, si trece singur peste schimbarea de ora
de vara. Se reimprospateaza din minut in minut. Ce randeaza serverul e ora de la generare, si
serveste de rezerva pentru cine are JavaScript oprit: aceeasi propozitie, un ceas care nu bate.
Punctul verde ramane aprins, fiindca acum insigna chiar e de acum.

Scriptul e inline, in pagina, langa insigna. CSP-ul sitului admite `'unsafe-inline'` pe
`script-src`, deci nu cere nici fisier nou, nici bump de versiune pe `/assets/*`, care e servit
immutable un an.

    python3 pas_live.py --repo <cale>
    python3 pas_live.py --repo <cale> --apply
"""
import argparse
import datetime
import glob
import io
import json
import os
import re

MARCA = "lv-b"
CSS = '<link rel="stylesheet" href="/assets/live-v1.css">'
ANCORA_CSS = '<link rel="stylesheet" href="/assets/pagini-v34.css">'

LUNI = {
    "ro": ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie", "august",
           "septembrie", "octombrie", "noiembrie", "decembrie"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"],
    "uk": ["січня", "лютого", "березня", "квітня", "травня", "червня", "липня", "серпня",
           "вересня", "жовтня", "листопада", "грудня"],
    "he": ["בינואר", "בפברואר", "במרץ", "באפריל", "במאי", "ביוני", "ביולי", "באוגוסט",
           "בספטמבר", "באוקטובר", "בנובמבר", "בדצמבר"],
    "ar": ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس",
           "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
}

TEXTE = {
    "ro": {"eticheta": "Disponibilitate verificată cu dezvoltatorul", "intre": ", ora "},
    "en": {"eticheta": "Availability checked with the developer", "intre": ", "},
    "uk": {"eticheta": "Наявність перевірено із забудовником", "intre": ", "},
    "he": {"eticheta": "הזמינות נבדקה מול היזם", "intre": ", "},
    "ar": {"eticheta": "تم التحقق من التوفر مع المطوّر", "intre": "، "},
}

FUS = "Europe/Bucharest"

# Ceasul. Nu ia ora calculatorului care se uita, ci ora Romaniei, prin `timeZone`. Ora de vara
# nu se calculeaza de mana nicaieri: si eticheta, si `datetime`, ies din acelasi `formatToParts`.
CEAS = """<script>(function(){
var L=%(luni)s,S=%(intre)s,Z=%(fus)s;
function ceas(){
 var f=new Intl.DateTimeFormat("en-GB",{timeZone:Z,year:"numeric",month:"2-digit",day:"2-digit",
   hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:false,timeZoneName:"longOffset"});
 var p={};f.formatToParts(new Date()).forEach(function(x){p[x.type]=x.value});
 var dec=(p.timeZoneName||"GMT+00:00").replace("GMT","")||"+00:00";
 return {text:parseInt(p.day,10)+" "+L[parseInt(p.month,10)-1]+S+p.hour+":"+p.minute,
         iso:p.year+"-"+p.month+"-"+p.day+"T"+p.hour+":"+p.minute+":"+p.second+dec};
}
function bate(){
 var c=ceas();
 var n=document.querySelectorAll(".lv-b time");
 for(var i=0;i<n.length;i++){n[i].textContent=c.text;n[i].setAttribute("datetime",c.iso);}
}
try{bate();setInterval(bate,60000);}catch(e){}
})();</script>"""


def limba(rel):
    for parte in rel.replace("\\", "/").split("/"):
        if parte in ("en", "he", "ar", "uk"):
            return parte
    return "ro"


def insigna(lb, mom):
    """Insigna randata de server: rezerva pentru cine are JavaScript oprit."""
    T = TEXTE[lb]
    cand = "%d %s%s%s" % (mom.day, LUNI[lb][mom.month - 1], T["intre"], mom.strftime("%H:%M"))
    return ('\n<p class="%s lv-on"><span class="lv-p" aria-hidden="true"></span>'
            '<span class="lv-t">%s <time datetime="%s">%s</time></span></p>\n%s\n'
            % (MARCA, T["eticheta"], mom.isoformat(), cand,
               CEAS % {"luni": json.dumps(LUNI[lb], ensure_ascii=False),
                       "intre": json.dumps(T["intre"], ensure_ascii=False),
                       "fus": json.dumps(FUS)}))


def acum_ro():
    try:
        import zoneinfo
        return datetime.datetime.now(zoneinfo.ZoneInfo(FUS)).replace(microsecond=0)
    except Exception:
        # fara baza de fusuri (Windows fara tzdata): ora Romaniei vara, cu ceasul UTC
        return (datetime.datetime.now(datetime.timezone.utc)
                .astimezone(datetime.timezone(datetime.timedelta(hours=3)))
                .replace(microsecond=0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    mom = acum_ro()
    puse = 0
    tinte = (glob.glob(os.path.join(a.repo, "apartamente", "index.html"))
             + glob.glob(os.path.join(a.repo, "*", "apartamente", "index.html"))
             + glob.glob(os.path.join(a.repo, "preturi", "index.html"))
             + glob.glob(os.path.join(a.repo, "*", "preturi", "index.html")))
    for fp in sorted(set(tinte)):
        rel = os.path.relpath(fp, a.repo)
        lb = limba(rel)
        h = io.open(fp, encoding="utf-8").read()
        b = insigna(lb, mom)

        # se scot si insigna veche, si ceasul vechi, apoi se pun la loc amandoua: ora se
        # schimba la fiecare rulare, deci o garda pe simpla prezenta ar lasa un moment vechi.
        h2 = re.sub(r'\n?<p class="%s[^"]*">.*?</p>\n?' % MARCA, "", h, flags=re.S)
        h2 = re.sub(r'\n?<script>\(function\(\)\{\nvar L=\[.*?\}\)\(\);</script>\n?', "",
                    h2, flags=re.S)
        m = re.search(r'<p class="lead[^"]*"[^>]*>.*?</p>', h2, re.S)
        if not m:
            print("  ATENTIE  %s: nu gasesc paragraful lead, sarit" % rel)
            continue
        nou = h2[:m.end()] + b + h2[m.end():]
        if CSS not in nou:
            nou = (nou.replace(ANCORA_CSS, ANCORA_CSS + "\n" + CSS, 1)
                   if ANCORA_CSS in nou else nou.replace("</head>", CSS + "\n</head>", 1))
        if nou != h:
            puse += 1
            if a.apply:
                io.open(fp, "w", encoding="utf-8", newline="\n").write(nou)

    print("pas_live: %d pagini cu ceas viu la ora Romaniei, rezerva randata la %s  (%s)"
          % (puse, mom.strftime("%d %b %Y %H:%M %z"), "APLICAT" if a.apply else "PROBA"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
