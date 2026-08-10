#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Actualizeaza sitemap.xml, sitemap-index.xml si llms.txt pentru blogul pe 5 limbi."""
import json, os, re, sys, glob
from datetime import date

ENGINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLOG_REPO", "/tmp/apt")
POSTS = os.environ.get("BLOG_POSTS", os.path.join(os.path.dirname(ENGINE), "posts"))
SITE = "https://apartamenteinbucuresti.ro"
LANGS = ["ro", "en", "he", "ar", "uk"]
TODAY = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()

ORDER_TOT = json.load(open(os.path.join(POSTS, "ordine.json"), encoding="utf-8"))

# Articolele, cu datele lor. Sitemap-ul si llms.txt arata DOAR ce are publishAt trecut:
# un URL in sitemap care da 404 e cel mai prost semnal pe care il poti trimite unui crawler.
def _post(slug, lang="ro"):
    fp = os.path.join(POSTS, lang, slug + ".json")
    return json.load(open(fp, encoding="utf-8")) if os.path.exists(fp) else None

def _pub(p):   return (p or {}).get("publishAt") or (p or {}).get("publishedAt") or "9999-12-31"
def _mod(p):   return (p or {}).get("updatedAt") or _pub(p)

ORDER = [s for s in ORDER_TOT if _pub(_post(s)) <= TODAY]
AMANATE = [s for s in ORDER_TOT if s not in ORDER]
if AMANATE:
    print(f"  in asteptare, in afara sitemap-ului: {len(AMANATE)} -> "
          + ", ".join(f"{s} ({_pub(_post(s))})" for s in AMANATE[:4])
          + (" ..." if len(AMANATE) > 4 else ""))

def u(lang, slug=None):
    b = f"{SITE}/" if lang == "ro" else f"{SITE}/{lang}/"
    return b + "blog/" + (f"{slug}/" if slug else "")

def alts(slug):
    s = "".join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{u(l, slug)}"/>' for l in LANGS)
    return s + f'<xhtml:link rel="alternate" hreflang="x-default" href="{u("ro", slug)}"/>'

# ---------- sitemap.xml ----------
sm = open(os.path.join(REPO, "sitemap.xml"), encoding="utf-8").read()
urls = re.findall(r"<url>.*?</url>", sm, re.S)
pastrate = [x for x in urls if "/blog/" not in x]

blog_urls = [f"<url><loc>{u(l)}</loc><lastmod>{TODAY}</lastmod>{alts(None)}</url>" for l in LANGS]
for slug in ORDER:
    for l in LANGS:
        p = os.path.join(REPO, ("blog" if l == "ro" else f"{l}/blog"), slug, "index.html")
        if not os.path.exists(p):
            print(f"  ATENTIE: lipseste de pe disc {l}/{slug}, nu il pun in sitemap"); continue
        # lastmod = ultima atingere REALA a textului, nu ziua rularii. Un lastmod care se
        # muta singur la fiecare build il invata pe crawler ca datele noastre nu inseamna nimic.
        lm = _mod(_post(slug, l)) if _post(slug, l) else _mod(_post(slug))
        blog_urls.append(f"<url><loc>{u(l, slug)}</loc><lastmod>{lm}</lastmod>{alts(slug)}</url>")

head = sm[: sm.find("<url>")]
out = head + "\n".join(pastrate + blog_urls) + "\n</urlset>\n"
open(os.path.join(REPO, "sitemap.xml"), "w", encoding="utf-8", newline="\n").write(out)
print(f"sitemap.xml: {len(pastrate)} pagini pastrate + {len(blog_urls)} de blog = {len(pastrate)+len(blog_urls)} URL")

# ---------- sitemap-index.xml ----------
si_p = os.path.join(REPO, "sitemap-index.xml")
si = open(si_p, encoding="utf-8").read()
si = re.sub(r"(<loc>[^<]*sitemap\.xml</loc>\s*<lastmod>)[^<]*(</lastmod>)", rf"\g<1>{TODAY}\g<2>", si)
open(si_p, "w", encoding="utf-8", newline="\n").write(si)
print(f"sitemap-index.xml: lastmod {TODAY}")

# ---------- llms.txt ----------
posts = {}
for fp in glob.glob(os.path.join(POSTS, "ro", "*.json")):
    p = json.load(open(fp, encoding="utf-8")); posts.setdefault(p["slug"], p)

lines = ["## Ghiduri (blog)"]
lines.append(f"- [Blog, toate ghidurile]({u('ro')}): {len(ORDER)} ghiduri pentru cumpărători, "
             "disponibile în română, engleză, ebraică, arabă și ucraineană")
for slug in ORDER:
    p = posts.get(slug)
    if not p: continue
    d = (p.get("descriptionLlm") or p.get("description") or "").strip()
    lines.append(f"- [{p['title']}]({u('ro', slug)}): {d}")
lines.append("")
lines.append("Fiecare ghid există în cele 5 limbi, la aceeași cale, cu prefixul limbii: "
             f"{u('en','SLUG')}, {u('he','SLUG')}, {u('ar','SLUG')}, {u('uk','SLUG')}.")
bloc = "\n".join(lines)

ll_p = os.path.join(REPO, "llms.txt")
ll = open(ll_p, encoding="utf-8").read()
m = re.search(r"^## Ghiduri \(blog\).*?(?=^## |\Z)", ll, re.S | re.M)
assert m, "nu gasesc sectiunea Ghiduri (blog) in llms.txt"
ll = ll[: m.start()] + bloc + "\n\n" + ll[m.end():]
open(ll_p, "w", encoding="utf-8", newline="\n").write(ll)
print(f"llms.txt: sectiunea Ghiduri rescrisa, {len(ORDER)} ghiduri")
