#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intoarce articolele de blog EXISTENTE din HTML inapoi in JSON, ca sa intre in acelasi motor."""
import glob, json, os, re, html as H, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/posts-existente"
os.makedirs(OUT, exist_ok=True)

def one(fp):
    h = open(fp, encoding="utf-8").read()
    slug = fp.split("/blog/")[-1].replace("/index.html", "")
    g = lambda p, s=h, fl=0: (re.search(p, s, fl).group(1) if re.search(p, s, fl) else "")
    blocks = {}
    for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
        o = json.loads(b); blocks[o.get("@type")] = o
    bp = blocks.get("BlogPosting", {})
    body = h[h.find("<main"): h.find("</main>")]

    def parse_blocks(seg):
        out = []
        for pb in re.findall(r'<div class="pblock rv"[^>]*>(.*?)</div>', seg, re.S):
            for m2 in re.finditer(r"<(p|ul|h3)>(.*?)</\1>", pb, re.S):
                tag, inner = m2.group(1), m2.group(2).strip()
                if tag == "ul":
                    out.append({"t": "ul", "x": [x.strip() for x in re.findall(r"<li>(.*?)</li>", inner, re.S)]})
                else:
                    out.append({"t": "p" if tag == "p" else "h3", "x": inner})
        return out

    sections = []
    parts = re.split(r'<h2 class="rv"[^>]*>', body)
    intro = parse_blocks(parts[0])          # blocuri asezate INAINTE de primul h2
    has_byline = 'class="byline' in body
    for seg in parts[1:]:
        h2 = H.unescape(re.sub(r"<[^>]+>", "", seg.split("</h2>")[0])).strip()
        if h2.startswith("Întrebări") or h2.startswith("Intrebari"): continue
        rest = seg.split("</h2>", 1)[1] if "</h2>" in seg else ""
        blks = parse_blocks(rest)
        if blks: sections.append({"h2": h2, "blocks": blks})

    faq = [{"q": H.unescape(re.sub(r"<[^>]+>", "", q)).strip(),
            "a": H.unescape(re.sub(r"<[^>]+>", "", a)).strip()}
           for q, a in zip(re.findall(r'<div class="faq-q">(.*?)</div>', body, re.S),
                           re.findall(r'<div class="faq-a">(.*?)</div>', body, re.S))]

    m = re.search(r'<div class="read-also[^"]*"[^>]*>(.*)$', body, re.S)
    read_also = [{"href": hr, "label": H.unescape(lb).strip()} for hr, lb in
                 re.findall(r'<a href="([^"]+)">([^<]+)</a>', m.group(1) if m else "")]

    title = H.unescape(re.sub(r"<[^>]+>", "", g(r"<h1[^>]*>(.*?)</h1>", h, re.S))).strip()
    lead = g(r'<p class="lead rv"[^>]*>(.*?)</p>', h, re.S).strip()
    mins = g(r"·\s*(\d+)\s*minute de citit")
    return {
        "slug": slug,
        "title": title,
        "seoTitle": H.unescape(g(r"<title>(.*?)</title>", h, re.S)),
        "description": H.unescape(g(r'<meta name="description" content="([^"]*)"')),
        "descriptionLlm": H.unescape(g(r'<meta name="description:llm" content="([^"]*)"')) or bp.get("description", ""),
        "articleSection": H.unescape(g(r'<meta property="article:section" content="([^"]*)"')) or "Blog",
        "keywords": bp.get("keywords", ""),
        "readMinutes": int(mins) if mins else 5,
        "publishedAt": bp.get("datePublished", ""),
        "lead": lead,
        "intro": intro,
        "hasByline": has_byline,
        "sections": sections,
        "faq": faq,
        "ctaAfter": H.unescape(re.sub(r"<[^>]+>", "", g(r'<p class="after">(.*?)</p>', h, re.S))).strip(),
        "readAlso": read_also,
    }

EXISTENTE = ["apartamente-noi-bucuresti-2026", "apartamente-noi-titan-dristor",
             "apartament-2-sau-3-camere-cum-alegi", "cumperi-direct-de-la-proprietar",
             "de-ce-ilioara-residence", "ilioara-residence-bloc-nou-titan-dristor"]

for fp in sorted(glob.glob("/tmp/apt/blog/*/index.html")):
    slug = fp.split("/blog/")[-1].replace("/index.html", "")
    if slug not in EXISTENTE: continue
    p = one(fp)
    words = len(re.findall(r"\w+", json.dumps(p, ensure_ascii=False)))
    print(f"  {slug:40} h2={len(p['sections'])} faq={len(p['faq'])} readAlso={len(p['readAlso'])} cuvinte~{words}")
    json.dump(p, open(os.path.join(OUT, slug + ".json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
print(f"scrise in {OUT}")
