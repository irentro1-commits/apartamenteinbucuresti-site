#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gate pe paginile HTML generate: schema vs vizibil, meta, hreflang, structura."""
import glob, json, re, sys, html as H, difflib, os

SITE = "https://apartamenteinbucuresti.ro"
fails, warns = [], []
def F(p, m): fails.append(f"[{p}] {m}")
def W(p, m): warns.append(f"[{p}] {m}")

def strip(s):
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", H.unescape(s)).strip()

import os as _os
_r = _os.environ.get("BLOG_REPO", "/tmp/apt")
paths = sys.argv[1:] or sorted(glob.glob(f"{_r}/blog/*/index.html") + glob.glob(f"{_r}/??/blog/*/index.html"))
print(f"Verific {len(paths)} pagini\n")

for fp in paths:
    rel = fp.replace(_r, "").lstrip("/"); name = rel.replace("/index.html", "")
    h = open(fp, encoding="utf-8").read()

    # --- meta de baza
    t = re.search(r"<title>(.*?)</title>", h, re.S)
    if not t: F(name, "lipseste <title>")
    else:
        lt = len(H.unescape(t.group(1)))
        if lt > 60: F(name, f"<title> {lt} caractere")
    d = re.search(r'<meta name="description" content="([^"]*)"', h)
    if not d: F(name, "lipseste meta description")
    elif len(H.unescape(d.group(1))) > 155: F(name, f"meta description {len(H.unescape(d.group(1)))} caractere")
    slug = name.split("/")[-1]
    can = re.findall(r'<link rel="canonical" href="([^"]*)"', h)
    if len(can) != 1: F(name, f"{len(can)} canonical")
    elif not can[0].endswith(f"/blog/{slug}/"): F(name, f"canonical gresit: {can[0]}")

    # --- hreflang: 5 limbi + x-default, bidirectional pe acelasi slug
    hl = dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', h))
    for code in ["ro", "en", "he", "ar", "uk", "x-default"]:
        if code not in hl: F(name, f"lipseste hreflang {code}")
    for code, href in hl.items():
        if not href.endswith(f"/blog/{slug}/"): F(name, f"hreflang {code} arata catre {href}")

    # --- og
    for prop in ["og:title", "og:description", "og:url", "og:image", "og:type"]:
        if f'property="{prop}"' not in h: F(name, f"lipseste {prop}")

    # --- h1 unic + ierarhie
    h1 = re.findall(r"<h1[^>]*>(.*?)</h1>", h, re.S)
    if len(h1) != 1: F(name, f"{len(h1)} tag-uri h1")
    order = re.findall(r"<h([1-3])[^>]*>", h)
    prev = 0
    for lvl in [int(x) for x in order]:
        if prev and lvl > prev + 1: F(name, f"saritura de nivel h{prev} -> h{lvl}")
        prev = lvl

    # --- JSON-LD parsabil + tipurile asteptate
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)
    types = []
    for b in blocks:
        try: types.append(json.loads(b).get("@type"))
        except Exception as e: F(name, f"JSON-LD invalid: {e}")
    need_list = ["BreadcrumbList", "BlogPosting", "WebPage"]
    if '<div class="faq-q">' in h: need_list.append("FAQPage")   # schema doar daca FAQ-ul e vizibil
    for need in need_list:
        if need not in types: F(name, f"lipseste schema {need}")
    if "FAQPage" in types and '<div class="faq-q">' not in h: F(name, "FAQPage fara FAQ vizibil")

    # --- FAQPage trebuie sa oglindeasca EXACT blocul vizibil (anti schema-spam)
    faq_schema = None
    for b in blocks:
        o = json.loads(b)
        if o.get("@type") == "FAQPage": faq_schema = o
    vis_q = [strip(x) for x in re.findall(r'<div class="faq-q">(.*?)</div>', h, re.S)]
    vis_a = [strip(x) for x in re.findall(r'<div class="faq-a">(.*?)</div>', h, re.S)]
    if faq_schema:
        sq = [q["name"] for q in faq_schema["mainEntity"]]
        sa = [q["acceptedAnswer"]["text"] for q in faq_schema["mainEntity"]]
        if len(sq) != len(vis_q): F(name, f"FAQ: {len(sq)} in schema, {len(vis_q)} vizibile")
        else:
            for i, (a, b2) in enumerate(zip(sa, vis_a)):
                r = difflib.SequenceMatcher(None, a, b2).ratio()
                if r < 0.85: F(name, f"raspuns FAQ #{i+1} difera de vizibil (potrivire {r:.2f})")
            for i, (a, b2) in enumerate(zip(sq, vis_q)):
                if difflib.SequenceMatcher(None, a, b2).ratio() < 0.9:
                    F(name, f"intrebare FAQ #{i+1} difera de vizibil")

    # --- linkuri interne moarte (verificat pe disc)
    repo = _r
    for href in set(re.findall(r'href="(/[^"#?]*)"', h)):
        if "." in href.rsplit("/",1)[-1]: continue
        target = os.path.join(repo, href.strip("/"), "index.html")
        if href == "/": target = os.path.join(repo, "index.html")
        if not os.path.exists(target): W(name, f"link fara tinta pe disc: {href}")

    # --- igiena de text pe partea vizibila
    body = h[h.find("<main"): h.find("</main>")]
    vis = strip(body)
    for ch in "şŞţŢ":
        if ch in vis: F(name, f"cedila '{ch}' in textul vizibil")
    lang_pg = re.search(r'<html[^>]*lang="([a-z]{2})"', h)
    lang_pg = lang_pg.group(1) if lang_pg else "ro"
    if lang_pg not in ("uk",):        # in ucraineana tirele sunt punctuatie obligatorie
        for dsh in "—–":
            if dsh in vis: F(name, "liniuta lunga in textul vizibil")
        if re.search(r"(?<=[a-zăâîșț,]) - (?=[a-zăâîșț])", vis): F(name, "liniuta ca legatura in textul vizibil")
    if lang_pg in ("he", "ar") and 'dir="rtl"' not in h: F(name, "pagina RTL fara dir=rtl")
    if "wa.me/40774096700" not in h: F(name, "lipseste linkul WhatsApp cu numarul curent")
    if "0773 287 233" in h or "40773287233" in h: F(name, "a ramas numarul vechi de telefon")
    if "aggregateRating" in h: F(name, "a ramas aggregateRating")

    # --- P-K: reveal per sectiune, cu efect variat
    fx = re.findall(r'<h2 class="rv" data-fx="([^"]+)"', h)
    if len(set(fx)) < 2 and len(fx) > 2: F(name, f"acelasi efect de reveal pe toate sectiunile: {set(fx)}")
    if not fx: F(name, "zero h2 cu reveal")

    print(f"  {name:36} h2={len(fx)} faq={len(vis_q)} schema={len(types)} hreflang={len(hl)}")

print()
for w in warns: print("WARN ", w)
for f in fails: print("FAIL ", f)
print(f"\n=== {len(fails)} FAIL, {len(warns)} WARN ===")
sys.exit(1 if fails else 0)
