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

WA_SVG = ('<svg class="wa" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
 '<path d="M12 2.2c-5.4 0-9.8 4.3-9.8 9.7 0 1.7.5 3.4 1.3 4.8L2.2 21.8l5.2-1.4c1.4.8 2.9 1.2 4.6 1.2 5.4 0 9.8-4.3 '
 '9.8-9.7S17.4 2.2 12 2.2zm0 17.6c-1.5 0-2.9-.4-4.1-1.1l-.3-.2-3 .8.8-2.9-.2-.3c-.8-1.3-1.2-2.7-1.2-4.2 0-4.4 3.6-7.9 '
 '8-7.9s8 3.5 8 7.9-3.6 7.9-8 7.9zm4.4-5.9c-.2-.1-1.4-.7-1.6-.8-.2-.1-.4-.1-.6.1-.2.2-.7.8-.8 1-.1.2-.3.2-.5.1-.2-.1-1-.4-1.9-1.2-.7-.6-1.2-1.4-1.3-1.6-.1-.2 0-.4.1-.5l.4-.5c.1-.2.2-.3.3-.5.1-.2 0-.4 0-.5 0-.1-.6-1.4-.8-1.9-.2-.5-.4-.4-.6-.4h-.5c-.2 0-.5.1-.7.3-.2.2-.9.9-.9 2.1s.9 2.4 1 2.6c.1.2 1.8 2.8 4.4 3.9.6.3 1.1.4 1.5.6.6.2 1.2.2 1.6.1.5-.1 1.4-.6 1.6-1.1.2-.6.2-1 .1-1.1-.1-.2-.2-.2-.4-.3z"/></svg>')

LOGO_SVG = ('<svg class="lg" viewBox="0 0 64 64" width="24" height="24" aria-hidden="true">'
 '<rect x="5" y="5" width="54" height="54" rx="13" fill="none" stroke="#F5F0E1" stroke-width="5"/>'
 '<rect class="lg-bar" x="14" y="17" width="13" height="30" rx="4" fill="#E8B45A"/>'
 '<rect x="32" y="17" width="3.5" height="30" fill="#F5F0E1"/>'
 '<rect x="38" y="17" width="3.5" height="30" fill="#F5F0E1"/>'
 '<rect x="44" y="17" width="3.5" height="30" fill="#F5F0E1"/>'
 '<rect x="50" y="17" width="3.5" height="30" fill="#F5F0E1"/></svg>')

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


def head_meta(p, lang, today):
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
<meta property="article:published_time" content="{p.get('publishedAt', today)}">
<meta property="article:modified_time" content="{today}">
<meta property="article:section" content="{esc(p['articleSection'])}">
<meta name="twitter:title" content="{esc(p['seoTitle'])}">
<meta name="twitter:description" content="{esc(p['description'])}">
"""


def head_schema(p, lang, today):
    lg, u = L[lang], url_for(lang, p["slug"])
    j = lambda d: '<script type="application/ld+json">' + json.dumps(d, ensure_ascii=False) + "</script>\n"
    out = j({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":1,"name":lg["home"],"item":url_for(lang).replace("blog/","")},
        {"@type":"ListItem","position":2,"name":lg["blog"],"item":url_for(lang)},
        {"@type":"ListItem","position":3,"name":p["title"]}]})
    out += j({"@context":"https://schema.org","@type":"BlogPosting","@id":u+"#article",
        "headline":p["title"],"description":p["description"],
        "datePublished":p.get("publishedAt", today),"dateModified":today,
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


def localize(s, lang):
    if lang == "ro": return s
    return re.sub(r'href="(/[^"]*)"', lambda m: f'href="{loc(m.group(1), lang)}"', s)


def render_blocks(blocks, lang="ro"):
    out = []
    for b in blocks:
        if b["t"] == "p":    out.append(localize(f'<p>{b["x"]}</p>', lang))
        elif b["t"] == "h3": out.append(f'<h3>{esc(b["x"])}</h3>')
        elif b["t"] == "ul": out.append(localize("<ul>" + "".join(f"<li>{x}</li>" for x in b["x"]) + "</ul>", lang))
    return "".join(out)


def article(p, lang, today):
    lg = L[lang]
    root = "/" if lang == "ro" else f"/{lang}/"
    blog = root + "blog/"
    o = ['<main class="pw art">']
    o.append(f'<nav class="bc" aria-label="{lg["here"]}"><a href="{root}">{lg["home"]}</a> › '
             f'<a href="{blog}">{lg["blog"]}</a> › <span aria-current="page">{esc(p["title"])}</span></nav>')
    if p.get("hasByline", True):
        o.append(f'<div class="ameta rv" data-fx="rise">{lg["updated"]} {fmt_date(today, lang)} · '
                 f'{p["readMinutes"]} {lg["readTime"]}</div>')
        o.append(f'<div class="byline rv" data-fx="rise"><a class="av" href="{root}echipa-ilioara-residence/" '
             f'aria-label="{esc(lg["author"])}">{LOGO_SVG}</a><span class="bi">'
             f'<a class="bn" href="{root}echipa-ilioara-residence/"><b>{esc(lg["author"])}</b></a>'
             f'<span class="br">{esc(lg["authorRole"])}</span></span></div>')
    o.append(f'<h1 class="rv" data-fx="rise">{esc(p["title"])}</h1>')
    o.append(localize(f'<p class="lead rv" data-fx="rise">{p["lead"]}</p>', lang))
    if p.get("intro"):
        o.append('<div class="pblock rv" data-fx="rise">' + render_blocks(p["intro"], lang) + "</div>")

    for i, s in enumerate(p["sections"]):
        fx = FX[i % len(FX)]                      # P-K-02: variem efectul de la o sectiune la alta
        o.append(f'<h2 class="rv" data-fx="{fx}">{esc(s["h2"])}</h2>')
        o.append('<div class="pblock rv" data-fx="rise">' + render_blocks(s["blocks"], lang) + "</div>")

    if p["faq"]:
     o.append(f'<h2 class="rv" data-fx="slide">{lg["faqH"]}</h2>')
     o.append('<div class="faq rv" data-fx="rise">' + "".join(
        f'<div class="faq-item"><div class="faq-q">{esc(f["q"])}</div>'
        f'<div class="faq-a">{esc(f["a"])}</div></div>' for f in p["faq"]) + "</div>")

    msg = quote(lg["waMsg"].format(t=p["title"]))
    o.append(f'<div class="pcta rv" data-fx="rise">\n  <a class="btn" href="https://wa.me/{WA}?text={msg}">'
             f'{WA_SVG}{lg["waBtn"]}</a>\n  <p class="after">{esc(p["ctaAfter"])}</p>\n</div>')

    if not p["readAlso"]: return "\n".join(o) + "\n"
    ra = "".join(f'<a href="{loc(r["href"], lang)}">{esc(r["label"])}</a>' for r in p["readAlso"])
    o.append(f'<div class="read-also rv" data-fx="rise"><div class="rh">{lg["readAlso"]}</div>{ra}</div>')
    return "\n".join(o) + "\n"


def build(repo, posts_dir, lang, only=None, today=None):
    today = today or date.today().isoformat()
    sh = shell(repo, lang)
    made = []
    for fp in sorted(glob.glob(os.path.join(posts_dir, "*.json"))):
        p = json.load(open(fp, encoding="utf-8"))
        if only and p["slug"] not in only: continue
        html = (sh["head_pre"] + head_meta(p, lang, today) + head_schema(p, lang, today)
                + sh["style"] + fix_nav(sh["body_pre"], lang, p["slug"])
                + article(p, lang, today) + sh["body_post"])
        # html lang/dir vine din coaja de referinta a limbii, deci e deja corect
        out = path_for(repo, lang, p["slug"])
        write(out, html)
        made.append((p["slug"], len(html), out))
    return made


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--posts", default="/tmp/posts")
    ap.add_argument("--lang", default="ro")
    ap.add_argument("--only", default=None)
    ap.add_argument("--date", default=None)
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    made = build(a.repo, a.posts, a.lang, only, a.date)
    for slug, n, out in made:
        print(f"  {a.lang}  {slug:36} {n:6} octeti  ->  {os.path.relpath(out, a.repo)}")
    print(f"{len(made)} pagini scrise")
