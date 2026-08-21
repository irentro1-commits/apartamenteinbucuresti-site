#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genereaza pagina de index a blogului, in toate cele 5 limbi, din aceleasi fisiere JSON."""
import json, os, re, sys, glob, importlib.util
from datetime import date
from urllib.parse import quote

ENGINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLOG_REPO", os.path.dirname(ENGINE).rstrip("/").rsplit("/.engine",1)[0] if "/.engine" in ENGINE else "/tmp/apt")
POSTS = os.environ.get("BLOG_POSTS", os.path.join(os.path.dirname(ENGINE), "posts"))
spec = importlib.util.spec_from_file_location("bb", os.path.join(ENGINE, "build_blog.py"))
bb = importlib.util.module_from_spec(spec); spec.loader.exec_module(bb)
SITE, LANGS, WA = bb.SITE, bb.LANGS, bb.WA

# Ceasul: implicit ziua de la Bucuresti, dar se poate da unul fals ca argument, pentru probe.
AZI = sys.argv[1] if len(sys.argv) > 1 else bb.azi_ro()

# Ordinea cardurilor: intai valul nou pe intentie de cumparare, apoi articolele de proiect.
# Slugurile cu publishAt in viitor stau in ordine.json, dar NU ajung pe pagina: indexul
# arata exact ce e publicat, ca sitemap-ul si ca llms.txt. Un card care duce la o pagina
# inexistenta e un 404 pus de noi, cu mana.
ORDER = json.load(open(os.path.join(POSTS, "ordine.json"), encoding="utf-8"))

# RO ramane exact cum e pe site acum. Restul vin din traducerea sirurilor de index.
IX = {"ro": dict(
    seoTitle="Blog apartamente noi în blocuri noi construite | Ilioara",
    description="Ghiduri oneste despre cumpărarea unui apartament nou în bloc nou construit: prețuri, acte, zona Titan-Dristor, cum alegeți.",
    h1="Ghiduri pentru cine cumpără un apartament nou",
    badge="Apartamente direct de la dezvoltator",
    lead="Scriem despre ce întreabă oamenii înainte să cumpere: prețuri, acte, etape, zonă.<br>Scurt și fără povești.",
    cardLink="Citiți",
    ctaAfter="Întrebări la care nu am răspuns încă? Scrieți-ne pe WhatsApp.",
    breadcrumbBlog="Blog",
)}
IX.update(json.load(open(os.path.join(POSTS, "index-strings.json"), encoding="utf-8")))

WA_INDEX_MSG = {
    "ro": "Bună ziua! Am citit blogul și vreau detalii despre apartamente.",
    "en": "Hello! I read the blog and I would like details about the apartments.",
    "he": "שלום! קראתי את הבלוג ואשמח לפרטים על הדירות.",
    "ar": "مرحباً! قرأت المدونة وأود معرفة تفاصيل عن الشقق.",
    "uk": "Доброго дня! Я читав блог і хочу дізнатися більше про квартири.",
}


def posts_for(lang):
    """Doar articolele publicate. Restul exista in .engine/posts si nicaieri altundeva."""
    out = {}
    for fp in glob.glob(os.path.join(POSTS, lang, "*.json")):
        p = json.load(open(fp, encoding="utf-8"))
        if bb.publicat(p, AZI):
            out[p["slug"]] = p
    return out


def build(lang):
    lg, ix = bb.L[lang], IX[lang]
    root = "/" if lang == "ro" else f"/{lang}/"
    url = f"{SITE}{root}blog/"
    ps = posts_for(lang)
    # "lipseste" inseamna traducere care nu exista pe disc. Un articol nepublicat inca
    # NU lipseste: e la coada, si asta e normal.
    missing = [s for s in ORDER if s not in ps
               and not os.path.exists(os.path.join(POSTS, lang, s + ".json"))]
    if missing: print(f"  [{lang}] lipsesc traducerile: {missing}")

    # coaja: RO din indexul existent, restul dintr-o subpagina a limbii
    ref = os.path.join(REPO, "blog/index.html" if lang == "ro" else f"{lang}/preturi/index.html")
    h = bb.read(ref)
    head_pre = h[: h.find("<title>")]
    style = re.search(r"<style>.*?</style>", h, re.S).group(0)
    style += ('<style>.card .cmeta{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;'
              'font-size:.68rem;letter-spacing:.05em;text-transform:uppercase;opacity:.72;'
              'margin:0 0 10px;min-width:0}'
              '.card .cmeta .ct{border:1px solid currentColor;border-radius:999px;padding:2px 9px;'
              'white-space:nowrap;max-width:100%;overflow:hidden;text-overflow:ellipsis}'
              '.card .cmeta time{white-space:nowrap}</style>')
    body_pre = h[h.find("</head>"): h.find("<main")]
    body_post = h[h.find("</main>"):]

    # nav activ pe Blog + comutator de limba catre indexul fiecarei limbi
    bp = body_pre.replace('<a class="nl act"', '<a class="nl"')
    bp = re.sub(r'(<a class="nl" href="[^"]*") aria-current="page"', r"\1", bp)
    bp = re.sub(r'<a class="nl" href="/(?:[a-z]{2}/)?blog/"',
                f'<a class="nl act" href="{root}blog/" aria-current="page"', bp, count=1)
    bp = re.sub(r'(<a href="[^"]*"[^>]*?) aria-current="page"(>\s*<span class="no")', r"\1\2", bp)
    bp = re.sub(r'<a href="/(?:[a-z]{2}/)?blog/"(\s+style="[^"]*")?(>\s*<span class="no")',
                lambda m: f'<a href="{root}blog/"{m.group(1) or ""} aria-current="page"{m.group(2)}', bp, count=1)
    for pat in (r'<nav class="hlgs2".*?</nav>', r'<div class="mn-langs2".*?</div>'):
        m = re.search(pat, bp, re.S)
        if m:
            blk = m.group(0)
            def repl(mm):
                href = mm.group(1)
                for l2 in LANGS:
                    pref = "/" if l2 == "ro" else f"/{l2}/"
                    if href == pref or href.startswith(pref):
                        if l2 != "ro" or href == "/" or not re.match(r"^/[a-z]{2}/", href):
                            return f'href="{pref}blog/"'
                return mm.group(0)
            bp = bp[:m.start()] + re.sub(r'href="([^"]+)"', repl, blk) + bp[m.end():]

    # head
    alts = "".join(f'<link rel="alternate" hreflang="{l2}" href="{SITE}{"/" if l2=="ro" else "/"+l2+"/"}blog/">\n'
                   for l2 in LANGS)
    alts += f'<link rel="alternate" hreflang="x-default" href="{SITE}/blog/">\n'
    head = f"""<title>{bb.esc(ix['seoTitle'])}</title>
<meta name="description" content="{bb.esc(ix['description'])}">
<link rel="canonical" href="{url}">
{alts}<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<meta property="og:type" content="website">
<meta property="og:locale" content="{lg['og']}">
<meta property="og:site_name" content="Ilioara Residence">
<meta property="og:image" content="{SITE}/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta property="og:title" content="{bb.esc(ix['seoTitle'])}">
<meta property="og:description" content="{bb.esc(ix['description'])}">
<meta property="og:url" content="{url}">
<meta name="twitter:title" content="{bb.esc(ix['seoTitle'])}">
<meta name="twitter:description" content="{bb.esc(ix['description'])}">
<meta name="geo.region" content="RO-B">
<meta name="geo.placename" content="București">
"""
    j = lambda d: '<script type="application/ld+json">' + json.dumps(d, ensure_ascii=False) + "</script>\n"
    schema = j({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": lg["home"], "item": f"{SITE}{root}"},
        {"@type": "ListItem", "position": 2, "name": ix["breadcrumbBlog"], "item": url}]})
    schema += j({"@context": "https://schema.org", "@type": "Blog", "@id": url + "#blog",
        "url": url, "name": ix["h1"], "description": ix["description"], "inLanguage": lg["code"],
        "publisher": {"@id": f"{SITE}/#organization"},
        "blogPost": [{"@type": "BlogPosting", "@id": f"{SITE}{root}blog/{s}/#article",
                      "headline": ps[s]["title"], "url": f"{SITE}{root}blog/{s}/"}
                     for s in ORDER if s in ps]})
    schema += j({"@context": "https://schema.org", "@type": "ItemList", "@id": url + "#list",
        "itemListElement": [{"@type": "ListItem", "position": i + 1,
                             "url": f"{SITE}{root}blog/{s}/", "name": ps[s]["title"]}
                            for i, s in enumerate([x for x in ORDER if x in ps])]})

    # main
    cards = "".join(
        f'<a class="card rv" data-fx="pop" href="{root}blog/{s}/">'
        f'<div class="cmeta"><span class="ct">{bb.esc(ps[s]["articleSection"])}</span>'
        f'<time datetime="{bb.data_pub(ps[s])}">{bb.fmt_date(bb.data_pub(ps[s]), lang)}</time></div>'
        f'<h2 style="margin:0;font-size:1.12rem;text-wrap:balance">{bb.esc(ps[s]["title"])}</h2>'
        f'<p class="cm">{bb.esc(ps[s]["description"])}</p>'
        f'<span class="cl">{bb.esc(ix["cardLink"])}</span></a>'
        for s in ORDER if s in ps)
    msg = quote(WA_INDEX_MSG[lang])
    main = (f'<main class="pw">\n'
            f'<nav class="bc" aria-label="{bb.esc(lg["here"])}"><a href="{root}">{bb.esc(lg["home"])}</a> › '
            f'<span aria-current="page">{bb.esc(ix["breadcrumbBlog"])}</span></nav>\n'
            f'<h1 class="rv" data-fx="rise">{bb.esc(ix["h1"])}</h1>\n'
            f'<p class="bdgp rv" data-fx="pop">{bb.esc(ix["badge"])}</p>\n'
            f'<p class="lead rv" data-fx="rise">{ix["lead"]}</p>\n'
            f'<div class="grid">{cards}</div>\n'
            f'<div class="pcta rv" data-fx="rise">\n'
            f'  <a class="btn" href="https://wa.me/{WA}?text={msg}">{bb.WA_SVG}{bb.esc(lg["waBtn"])}</a>\n'
            f'  <p class="after">{bb.esc(ix["ctaAfter"])}</p>\n</div>\n')

    out = os.path.join(REPO, "blog/index.html" if lang == "ro" else f"{lang}/blog/index.html")
    bb.write(out, head_pre + head + schema + style + bp + main + body_post)
    return out, len(cards.split('class="card')) - 1


for lang in LANGS:
    out, n = build(lang)
    print(f"  {lang}  {n:2} carduri  ->  {os.path.relpath(out, REPO)}")
