#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generator de articole de blog pentru apartamenteinbucuresti.ro.

Ia coaja (head boilerplate + header + meniu + footer + scripturi) dintr-o pagina
existenta din repo si injecteaza continutul unui articol dat ca JSON.
Motorul e acelasi pentru articolele scrise acum si pentru coada zilnica.

  python3 build_blog.py --repo /tmp/apt --posts /tmp/posts --lang ro
  python3 build_blog.py --repo /tmp/apt --posts /tmp/posts --lang ro --only slug1,slug2
  python3 build_blog.py --repo /tmp/apt --hreflang        # doar re-scrie blocul hreflang peste tot

P-U-01/P-U-02: totul trece prin Python, cu utf-8 explicit, fiindca PowerShell corupe diacriticele.
"""
import argparse, json, os, re, sys, glob
from datetime import date
from urllib.parse import quote

SITE = "https://apartamenteinbucuresti.ro"
WA = "40774096700"
LANGS = ["ro", "en", "he", "ar", "uk"]

# Cate o coaja de referinta per limba. RO ia dintr-un articol de blog existent,
# restul dintr-o subpagina traduse, fiindca blogul inca nu exista in limba aia.
REF = {
    "ro": "blog/apartamente-noi-titan-dristor/index.html",
    "en": "en/preturi/index.html",
    "he": "he/preturi/index.html",
    "ar": "ar/preturi/index.html",
    "uk": "uk/preturi/index.html",
}

L = {
 "ro": dict(code="ro-RO", og="ro_RO", home="Acasă", blog="Blog", here="Ești aici",
            faqH="Întrebări frecvente", readAlso="Citește și", updated="Actualizat",
            readTime="minute de citit", waBtn="Scrie-ne pe WhatsApp",
            author="Echipa Ilioara Residence",
            authorRole="Oamenii care construiesc și vând Ilioara Residence, direct",
            waMsg='Bună ziua! Am citit articolul "{t}" și vreau detalii.',
            months=["ianuarie","februarie","martie","aprilie","mai","iunie","iulie",
                    "august","septembrie","octombrie","noiembrie","decembrie"]),
 "en": dict(code="en", og="en_US", home="Home", blog="Blog", here="You are here",
            faqH="Frequently asked questions", readAlso="Read next", updated="Updated",
            readTime="min read", waBtn="Message us on WhatsApp",
            author="The Ilioara Residence team",
            authorRole="The people who build and sell Ilioara Residence, directly",
            waMsg='Hello! I read the article "{t}" and I would like more details.',
            months=["January","February","March","April","May","June","July",
                    "August","September","October","November","December"]),
 "he": dict(code="he", og="he_IL", home="בית", blog="בלוג", here="אתה נמצא כאן",
            faqH="שאלות נפוצות", readAlso="קראו גם", updated="עודכן",
            readTime="דקות קריאה", waBtn="כתבו לנו בוואטסאפ",
            author="צוות Ilioara Residence",
            authorRole="האנשים שבונים ומוכרים את Ilioara Residence, ישירות",
            waMsg='שלום! קראתי את הכתבה "{t}" ואשמח לפרטים.',
            months=["ינואר","פברואר","מרץ","אפריל","מאי","יוני","יולי",
                    "אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]),
 "ar": dict(code="ar", og="ar_AR", home="الرئيسية", blog="مدونة", here="أنت هنا",
            faqH="الأسئلة الشائعة", readAlso="اقرأ أيضاً", updated="آخر تحديث",
            readTime="دقائق قراءة", waBtn="راسلنا على واتساب",
            author="فريق Ilioara Residence",
            authorRole="من يبنون ويبيعون Ilioara Residence مباشرة",
            waMsg='مرحباً! قرأت المقال "{t}" وأود معرفة التفاصيل.',
            months=["يناير","فبراير","مارس","أبريل","مايو","يونيو","يوليو",
                    "أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"]),
 "uk": dict(code="uk", og="uk_UA", home="Головна", blog="Блог", here="Ви тут",
            faqH="Часті запитання", readAlso="Читайте також", updated="Оновлено",
            readTime="хв читання", waBtn="Напишіть нам у WhatsApp",
            author="Команда Ilioara Residence",
            authorRole="Люди, які будують і продають Ilioara Residence, напряму",
            waMsg='Доброго дня! Я прочитав статтю "{t}" і хочу дізнатися більше.',
            months=["січня","лютого","березня","квітня","травня","червня","липня",
                    "серпня","вересня","жовтня","листопада","грудня"]),
}

# ------------------------------------------------------- DATELE: publicarea e o DATA, nu un cron
# `publishAt` = ziua din care articolul e public. Pana atunci exista in .engine/posts si NICAIERI
# altundeva: fara pagina, fara card in index, fara sitemap, fara llms.txt.
# `updatedAt` = ultima zi in care s-a atins TEXTUL. Implicit, ziua publicarii.
#
# LECTIE 10 AUG 2026: `dateModified` era `today`, adica ziua rularii. Doua efecte, amandoua rele.
# Unu, site-ul scria "Actualizat azi" pe articole pe care nu le atinsese nimeni de saptamani, adica
# mintea cititorul si Google deopotriva. Doi, orice regenerare producea un diff pe toate cele 55 de
# pagini, deci nu se mai putea vedea ce s-a schimbat CU ADEVARAT. O data care se muta singura face
# imposibila verificarea prin diff, si verificarea prin diff e singura care nu oboseste.
def data_pub(p):
    d = p.get("publishAt") or p.get("publishedAt")
    if not d:
        raise SystemExit(f"FAIL: articolul {p.get('slug')} nu are publishAt. "
                         "Fara data de publicare nu se genereaza nimic.")
    return d


def data_mod(p):
    return p.get("updatedAt") or data_pub(p)


def azi_ro():
    """Ziua la Bucuresti. Workflow-ul ruleaza pe UTC, deci fusul se scrie explicit:
    la 02:00 ora Bucurestiului, in UTC e inca ziua de ieri."""
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Bucharest")).date().isoformat()
    except Exception:
        return date.today().isoformat()


def publicat(p, azi=None):
    return data_pub(p) <= (azi or azi_ro())


WA_SVG = ('<svg class="wa" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
 '<path d="M12 2.2c-5.4 0-9.8 4.3-9.8 9.7 0 1.7.5 3.4 1.3 4.8L2.2 21.8l5.2-1.4c1.4.8 2.9 1.2 4.6 1.2 5.4 0 9.8-4.3 '
 '9.8-9.7S17.4 2.2 12 2.2zm0 17.6c-1.5 0-2.9-.4-4.1-1.1l-.3-.2-3 .8.8-2.9-.2-.3c-.8-1.3-1.2-2.7-1.2-4.2 0-4.4 3.6-7.9 '
 '8-7.9s8 3.5 8 7.9-3.6 7.9-8 7.9zm4.4-5.9c-.2-.1-1.4-.7-1.6-.8-.2-.1-.4-.1-.6.1-.2.2-.7.8-.8 1-.1.2-.3.2-.5.1-.2-.1-1-.4-1.9-1.2-.7-.6-1.2-1.4-1.3-1.6-.1-.2 0-.4.1-.5l.4-.5c.1-.2.2-.3.3-.5.1-.2 0-.4 0-.5 0-.1-.6-1.4-.8-1.9-.2-.5-.4-.4-.6-.4h-.5c-.2 0-.5.1-.7.3-.2.2-.9.9-.9 2.1s.9 2.4 1 2.6c.1.2 1.8 2.8 4.4 3.9.6.3 1.1.4 1.5.6.6.2 1.2.2 1.6.1.5-.1 1.4-.6 1.6-1.1.2-.6.2-1 .1-1.1-.1-.2-.2-.2-.4-.3z"/></svg>')

# Marca reala Ilioara Residence (comit 0b6ad4f, 4 aug 2026), la 34px cat e in byline.
# Culorile sunt variabile de tema, NU hexuri fixe: marca trebuie sa se intoarca pe tema deschisa.
# Aici a stat pana pe 10 aug 2026 marca VECHE, cu #F5F0E1 si #E8B45A. Nu a deranjat pe nimeni
# fiindca nimeni nu a mai regenerat un articol dupa schimbarea marcii: generatorul mergea in gol,
# si prima regenerare automata ar fi pus logoul vechi inapoi pe 55 de pagini deodata.
# Un generator nerulat nu e un generator corect, e unul netestat.
LOGO_SVG = ('<svg class="lg" viewBox="0 0 64 64" width="24" height="24" aria-hidden="true">'
 '<rect x="1.83" y="1.83" width="60.34" height="60.34" rx="8.23" fill="none" '
 'stroke="var(--logo-ink)" stroke-width="3.89"/>'
 '<rect class="lg-bar" x="10.06" y="10.06" width="14.63" height="43.89" rx="2.74" '
 'fill="var(--logo-gold)"/>'
 '<rect x="29.26" y="10.06" width="4.11" height="43.89" rx="0.91" fill="var(--logo-ink)"/>'
 '<rect x="36.11" y="10.06" width="4.11" height="43.89" rx="0.91" fill="var(--logo-ink)"/>'
 '<rect x="42.97" y="10.06" width="4.11" height="43.89" rx="0.91" fill="var(--logo-ink)"/>'
 '<rect x="49.83" y="10.06" width="4.11" height="43.89" rx="0.91" fill="var(--logo-ink)"/></svg>')

FX = ["slide", "rise", "blur", "pop", "slide"]   # P-K-02: variem efectul intre sectiuni


def read(p):  return open(p, encoding="utf-8").read()
def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f: f.write(s)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def url_for(lang, slug=None):
    base = f"{SITE}/" if lang == "ro" else f"{SITE}/{lang}/"
    if slug is None: return base + "blog/"
    return base + f"blog/{slug}/"


def path_for(repo, lang, slug):
    d = "blog" if lang == "ro" else f"{lang}/blog"
    return os.path.join(repo, d, slug, "index.html")


def shell(repo, lang):
    """Sparge pagina de referinta in bucatile refolosibile."""
    h = read(os.path.join(repo, REF[lang]))
    style = re.search(r"<style>.*?</style>", h, re.S).group(0)
    return dict(
        head_pre = h[: h.find("<title>")],
        style    = style,
        body_pre = h[h.find("</head>") : h.find("<main")],
        body_post= h[h.find("</main>") :],
    )


def _swap_lang_block(block, slug):
    """Inauntrul UNUI bloc de comutare a limbii, repunctam fiecare href catre articolul din limba lui.
    Lucram doar pe blocul izolat, ca sa nu atingem logoul, meniul sau restul navigatiei."""
    def repl(m):
        href = m.group(1)
        for l2 in LANGS:
            pref = "/" if l2 == "ro" else f"/{l2}/"
            # linkul de limba arata fie catre radacina limbii, fie catre pagina echivalenta
            if href == pref or href.startswith(pref):
                if l2 != "ro" or href == "/" or not re.match(r"^/[a-z]{2}/", href):
                    return f'href="{pref}blog/{slug}/"'
        return m.group(0)
    return re.sub(r'href="([^"]+)"', repl, block)


def fix_nav(body_pre, lang, slug):
    """Muta marcajul de pagina activa pe Blog si repunctam comutatoarele de limba.
    Chirurgical: atinge DOAR blocurile de limba si DOAR linkurile de navigatie catre blog."""
    bp = body_pre
    blog_href = "/blog/" if lang == "ro" else f"/{lang}/blog/"

    # 1. bara de sus: scoate marcajul activ de oriunde ar fi si pune-l pe Blog
    bp = bp.replace('<a class="nl act"', '<a class="nl"')
    bp = re.sub(r'(<a class="nl" href="[^"]*") aria-current="page"', r"\1", bp)
    bp = re.sub(r'<a class="nl" href="/(?:[a-z]{2}/)?blog/"',
                f'<a class="nl act" href="{blog_href}" aria-current="page"', bp, count=1)

    # 2. panoul de meniu: acelasi lucru, pe intrarile numerotate
    bp = re.sub(r'(<a href="[^"]*"[^>]*?) aria-current="page"(>\s*<span class="no")', r"\1\2", bp)
    bp = re.sub(r'<a href="/(?:[a-z]{2}/)?blog/"(\s+style="[^"]*")?(>\s*<span class="no")',
                lambda m: f'<a href="{blog_href}"{m.group(1) or ""} aria-current="page"{m.group(2)}', bp, count=1)

    # 3. comutatoarele de limba, fiecare tratat ca bloc inchis
    for pat in (r'<nav class="hlgs2".*?</nav>', r'<div class="mn-langs2".*?</div>'):
        m = re.search(pat, bp, re.S)
        if m: bp = bp[:m.start()] + _swap_lang_block(m.group(0), slug) + bp[m.end():]
    return bp


def head_meta(p, lang):
    lg, u = L[lang], url_for(lang, p["slug"])
    alts = "".join(f'<link rel="alternate" hreflang="{L[l2]["code"].split("-")[0]}" href="{url_for(l2, p["slug"])}">\n'
                   for l2 in LANGS)
    alts += f'<link rel="alternate" hreflang="x-default" href="{url_for("ro", p["slug"])}">\n'
    return f"""<title>{esc(p['seoTitle'])}</title>
<meta name="description" content="{esc(p['description'])}">
<link rel="canonical" href="{u}">
{alts}<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<meta property="og:type" content="article">
<meta property="og:locale" content="{lg['og']}">
<meta property="og:site_name" content="Ilioara Residence">
<meta property="og:image" content="{SITE}/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta property="og:title" content="{esc(p['seoTitle'])}">
<meta property="og:description" content="{esc(p['description'])}">
<meta property="og:url" content="{u}">
<meta name="geo.region" content="RO-B">
<meta name="geo.placename" content="București">
<meta name="geo.position" content="44.4179;26.1478">
<meta name="ICBM" content="44.4179, 26.1478">
<meta name="author" content="{esc(lg['author'])}">
<meta name="description:llm" content="{esc(p['descriptionLlm'])}">
<meta property="article:published_time" content="{data_pub(p)}">
<meta property="article:modified_time" content="{data_mod(p)}">
<meta property="article:section" content="{esc(p['articleSection'])}">
<meta name="twitter:title" content="{esc(p['seoTitle'])}">
<meta name="twitter:description" content="{esc(p['description'])}">
"""


def head_schema(p, lang):
    lg, u = L[lang], url_for(lang, p["slug"])
    j = lambda d: '<script type="application/ld+json">' + json.dumps(d, ensure_ascii=False) + "</script>\n"
    out = j({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":1,"name":lg["home"],"item":url_for(lang).replace("blog/","")},
        {"@type":"ListItem","position":2,"name":lg["blog"],"item":url_for(lang)},
        {"@type":"ListItem","position":3,"name":p["title"]}]})
    out += j({"@context":"https://schema.org","@type":"BlogPosting","@id":u+"#article",
        "headline":p["title"],"description":p["description"],
        "datePublished":data_pub(p),"dateModified":data_mod(p),
        "inLanguage":lg["code"],
        "mainEntityOfPage":{"@type":"WebPage","@id":u},
        "image":{"@type":"ImageObject","url":f"{SITE}/og.jpg","width":1200,"height":630},
        "author":{"@type":"Organization","name":lg["author"],
                  "url":(url_for(lang).replace("blog/","")) + "echipa-ilioara-residence/"},
        "publisher":{"@id":f"{SITE}/#organization","@type":"Organization","name":"Ilioara Residence",
                     "logo":{"@type":"ImageObject","url":f"{SITE}/favicon-512.png","width":512,"height":512}},
        "isPartOf":{"@id":f"{SITE}/#residence"},
        "articleSection":p["articleSection"],"keywords":p["keywords"]})
    # FAQPage: acelasi text ca blocul vizibil, cuvant cu cuvant (regula anti schema-spam)
    if p["faq"]:
        out += j({"@context":"https://schema.org","@type":"FAQPage","@id":u+"#faq","inLanguage":lg["code"],
            "mainEntity":[{"@type":"Question","name":f["q"],
                           "acceptedAnswer":{"@type":"Answer","text":f["a"]}} for f in p["faq"]]})
    out += j({"@context":"https://schema.org","@type":"WebPage","url":u,
        "speakable":{"@type":"SpeakableSpecification","cssSelector":["h1",".lead",".faq-q"]}})
    return out


def fmt_date(d, lang):
    y, m, dd = (int(x) for x in d.split("-"))
    mn = L[lang]["months"][m-1]
    if lang == "ro": return f"{dd} {mn} {y}"
    if lang == "en": return f"{mn} {dd}, {y}"
    if lang == "uk": return f"{dd} {mn} {y}"
    return f"{dd} {mn} {y}"


LOCAL_ROOTS = ("/apartamente/","/preturi/","/dotari/","/credit-ipotecar/","/zona/","/parcare/",
  "/proiecte-finalizate/","/pentru-cine-construim/","/echipa-ilioara-residence/","/informatii-legale/",
  "/apartamente-noi-bucuresti/","/blocuri-noi-bucuresti/","/apartamente-blocuri-noi-bucuresti/","/blog/")


def loc(href, lang):
    """Duce un link intern RO catre varianta din limba curenta. Externele raman neatinse."""
    if lang == "ro" or not href.startswith("/"): return href
    if href == "/": return f"/{lang}/"
    if href.startswith("/blog/") or href in LOCAL_ROOTS or href.startswith(tuple(LOCAL_ROOTS)):
        return f"/{lang}{href}"
    return href


def desfa_amanate(s, nepublicate):
    """Legatura din PROZA catre un articol inca nepublicat: se scoate ancora, textul ramane.

    `readAlso` era filtrat, dar legaturile din corpul textului nu. Proba pe ceas fals, 10 aug
    2026: un singur articol amanat lasa in urma 15 legaturi catre o pagina inexistenta, in
    cinci limbi. Fraza ramane intreaga si citibila; ancora se intoarce singura in ziua in care
    apare tinta, fiindca rularea zilnica regenereaza tot ce e publicat.
    """
    if not nepublicate: return s
    def per(m):
        slug = m.group(1)
        return m.group(2) if slug in nepublicate else m.group(0)
    return re.sub(r'<a href="/blog/([^/"]+)/"[^>]*>(.*?)</a>', per, s, flags=re.S)


def localize(s, lang, nepublicate=frozenset()):
    s = desfa_amanate(s, nepublicate)
    if lang == "ro": return s
    return re.sub(r'href="(/[^"]*)"', lambda m: f'href="{loc(m.group(1), lang)}"', s)


def render_blocks(blocks, lang="ro", nepublicate=frozenset()):
    out = []
    for b in blocks:
        if b["t"] == "p":    out.append(localize(f'<p>{b["x"]}</p>', lang, nepublicate))
        elif b["t"] == "h3": out.append(f'<h3>{esc(b["x"])}</h3>')
        elif b["t"] == "ul": out.append(localize("<ul>" + "".join(f"<li>{x}</li>" for x in b["x"]) + "</ul>", lang, nepublicate))
    return "".join(out)


def article(p, lang, nepublicate=frozenset()):
    lg = L[lang]
    root = "/" if lang == "ro" else f"/{lang}/"
    blog = root + "blog/"
    o = ['<main class="pw art">']
    o.append(f'<nav class="bc" aria-label="{lg["here"]}"><a href="{root}">{lg["home"]}</a> › '
             f'<a href="{blog}">{lg["blog"]}</a> › <span aria-current="page">{esc(p["title"])}</span></nav>')
    if p.get("hasByline", True):
        o.append(f'<div class="ameta rv" data-fx="rise">{lg["updated"]} {fmt_date(data_mod(p), lang)} · '
                 f'{p["readMinutes"]} {lg["readTime"]}</div>')
        o.append(f'<div class="byline rv" data-fx="rise"><a class="av" href="{root}echipa-ilioara-residence/" '
             f'aria-label="{esc(lg["author"])}">{LOGO_SVG}</a><span class="bi">'
             f'<a class="bn" href="{root}echipa-ilioara-residence/"><b>{esc(lg["author"])}</b></a>'
             f'<span class="br">{esc(lg["authorRole"])}</span></span></div>')
    o.append(f'<h1 class="rv" data-fx="rise">{esc(p["title"])}</h1>')
    o.append(localize(f'<p class="lead rv" data-fx="rise">{p["lead"]}</p>', lang, nepublicate))
    if p.get("intro"):
        o.append('<div class="pblock rv" data-fx="rise">' + render_blocks(p["intro"], lang, nepublicate) + "</div>")

    for i, s in enumerate(p["sections"]):
        fx = FX[i % len(FX)]                      # P-K-02: variem efectul de la o sectiune la alta
        o.append(f'<h2 class="rv" data-fx="{fx}">{esc(s["h2"])}</h2>')
        o.append('<div class="pblock rv" data-fx="rise">' + render_blocks(s["blocks"], lang, nepublicate) + "</div>")

    if p["faq"]:
     o.append(f'<h2 class="rv" data-fx="slide">{lg["faqH"]}</h2>')
     o.append('<div class="faq rv" data-fx="rise">' + "".join(
        f'<div class="faq-item"><div class="faq-q">{esc(f["q"])}</div>'
        f'<div class="faq-a">{esc(f["a"])}</div></div>' for f in p["faq"]) + "</div>")

    msg = quote(lg["waMsg"].format(t=p["title"]))
    o.append(f'<div class="pcta rv" data-fx="rise">\n  <a class="btn" href="https://wa.me/{WA}?text={msg}">'
             f'{WA_SVG}{lg["waBtn"]}</a>\n  <p class="after">{esc(p["ctaAfter"])}</p>\n</div>')

    # "Citeste si" trimite DOAR spre articole deja publicate. Un articol care iese peste
    # patru zile n-are inca pagina, deci un link spre el ar fi un 404 pus de noi, cu mana.
    ra_ok, ra_amanate = [], []
    for r in p.get("readAlso") or []:
        (ra_amanate if _viitor(r["href"], nepublicate) else ra_ok).append(r)
    for r in ra_amanate:
        print(f"    [{lang}] {p['slug']}: legatura amanata catre {r['href']}")
    if not ra_ok: return "\n".join(o) + "\n"
    ra = "".join(f'<a href="{loc(r["href"], lang)}">{esc(r["label"])}</a>' for r in ra_ok)
    o.append(f'<div class="read-also rv" data-fx="rise"><div class="rh">{lg["readAlso"]}</div>{ra}</div>')
    return "\n".join(o) + "\n"


def _viitor(href, nepublicate):
    """href de forma /blog/<slug>/ care arata spre un articol inca nepublicat."""
    m = re.match(r"^/blog/([^/]+)/$", href or "")
    return bool(m) and m.group(1) in nepublicate


def build(repo, posts_dir, lang, only=None, azi=None, tot=False):
    """Scrie paginile articolelor PUBLICATE. `tot=True` le scrie pe toate, pentru
    previzualizare locala: util cand vrei sa vezi cum arata articolul de peste doua zile."""
    azi = azi or azi_ro()
    sh = shell(repo, lang)
    posts = [json.load(open(fp, encoding="utf-8"))
             for fp in sorted(glob.glob(os.path.join(posts_dir, "*.json")))]
    nepublicate = {p["slug"] for p in posts if not publicat(p, azi)} if not tot else set()
    made, amanate = [], []
    for p in posts:
        if only and p["slug"] not in only: continue
        if not tot and not publicat(p, azi):
            amanate.append((p["slug"], data_pub(p)))
            continue
        html = (sh["head_pre"] + head_meta(p, lang) + head_schema(p, lang)
                + sh["style"] + fix_nav(sh["body_pre"], lang, p["slug"])
                + article(p, lang, nepublicate) + sh["body_post"])
        # html lang/dir vine din coaja de referinta a limbii, deci e deja corect
        out = path_for(repo, lang, p["slug"])
        write(out, html)
        made.append((p["slug"], len(html), out))
    return made, amanate


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--posts", default="/tmp/posts")
    ap.add_argument("--lang", default="ro")
    ap.add_argument("--only", default=None)
    ap.add_argument("--azi", default=None, help="ceas fals, pentru probe: AAAA-LL-ZZ")
    ap.add_argument("--tot", action="store_true", help="scrie si articolele inca nepublicate")
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    made, amanate = build(a.repo, a.posts, a.lang, only, a.azi, a.tot)
    for slug, n, out in made:
        print(f"  {a.lang}  {slug:36} {n:6} octeti  ->  {os.path.relpath(out, a.repo)}")
    for slug, d in amanate:
        print(f"  {a.lang}  {slug:36} inca nepublicat, iese pe {d}")
    print(f"{len(made)} pagini scrise, {len(amanate)} in asteptare")
