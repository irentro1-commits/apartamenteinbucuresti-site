#!/usr/bin/env python3
"""Gate pe batch-ul de articole (blog-seo). Exit 1 la FAIL."""
import json, re, sys, glob, os, unicodedata

ALLOWED = {
 "/", "/apartamente/", "/preturi/", "/dotari/", "/credit-ipotecar/", "/zona/",
 "/parcare/", "/proiecte-finalizate/", "/pentru-cine-construim/",
 "/echipa-ilioara-residence/", "/blog/", "/informatii-legale/",
 "/apartamente-noi-bucuresti/", "/blocuri-noi-bucuresti/",
 "/apartamente-blocuri-noi-bucuresti/",
}
KNOWN_BLOG = {
 "apartamente-noi-bucuresti-2026","apartamente-noi-titan-dristor",
 "apartament-2-sau-3-camere-cum-alegi","cumperi-direct-de-la-proprietar",
 "de-ce-ilioara-residence","ilioara-residence-bloc-nou-titan-dristor",
 # val nou
 "tva-apartamente-noi-2026","costuri-reale-apartament-nou",
 "credit-ipotecar-apartament-nou","suprafata-utila-vs-construita",
 "apartamente-langa-metrou-bucuresti",
}
REQ = ["slug","title","seoTitle","description","descriptionLlm","articleSection",
       "keywords","readMinutes","lead","sections","faq","ctaAfter","readAlso"]
CEDILLA = "şŞţŢ"
AI_OPEN = ["Desigur","Absolut","Iată un","În concluzie","În era digitală",
           "Este important de menționat","Merită menționat că","În lumea de azi"]
DASHES = ["—","–","‒","―"]

fails, warns = [], []
def F(slug,msg): fails.append(f"[{slug}] {msg}")
def W(slug,msg): warns.append(f"[{slug}] {msg}")

def texts(p):
    """toate sirurile vizibile din articol"""
    out=[p["title"],p["seoTitle"],p["description"],p["descriptionLlm"],p["lead"],p["ctaAfter"]]
    for s in p["sections"]:
        out.append(s["h2"])
        for b in s["blocks"]:
            out.extend(b["x"] if isinstance(b["x"],list) else [b["x"]])
    for f in p["faq"]: out += [f["q"], f["a"]]
    for r in p["readAlso"]: out.append(r["label"])
    return out

files = sorted(glob.glob("/tmp/posts/*.json"))
if not files: print("ZERO fisiere in /tmp/posts"); sys.exit(1)
print(f"Validez {len(files)} articole\n")

for fp in files:
    p = json.load(open(fp, encoding="utf-8"))
    slug = p.get("slug","?")
    for k in REQ:
        if k not in p: F(slug, f"lipseste cheia '{k}'")
    if os.path.basename(fp) != slug + ".json":
        F(slug, f"numele fisierului nu se potriveste cu slug")

    # lungimi, numarate in CARACTERE nu bytes
    lt, ld = len(p["seoTitle"]), len(p["description"])
    if lt > 60: F(slug, f"seoTitle {lt} caractere, peste 60")
    elif lt > 58: W(slug, f"seoTitle {lt} caractere, la limita")
    if ld > 155: F(slug, f"description {ld} caractere, peste 155")
    elif ld > 152: W(slug, f"description {ld} caractere, la limita")

    allt = texts(p)
    blob = "\n".join(allt)

    # cedila interzisa
    for ch in CEDILLA:
        if ch in blob:
            n = blob.count(ch)
            ctx = [t[max(0,t.find(ch)-30):t.find(ch)+30] for t in allt if ch in t][:2]
            F(slug, f"cedila '{ch}' x{n} (cere virgula dedesubt). Context: {ctx}")

    # liniuta lunga / scurta
    for d in DASHES:
        if d in blob:
            ctx=[t[max(0,t.find(d)-40):t.find(d)+40] for t in allt if d in t][:2]
            F(slug, f"liniuta lunga U+{ord(d):04X}. Context: {ctx}")
    for t in allt:
        for m in re.finditer(r"(?<=[a-zăâîșțA-ZĂÂÎȘȚ,]) - (?=[a-zăâîșțA-ZĂÂÎȘȚ])", t):
            F(slug, f"liniuta folosita ca legatura: ...{t[max(0,m.start()-40):m.end()+40]}...")

    # deschideri de robot
    for t in allt:
        for a in AI_OPEN:
            if t.strip().startswith(a): F(slug, f"deschidere de robot '{a}' in: {t[:70]}")

    # diacritice prezente (articol RO fara nicio diacritica = agent care a returnat ASCII)
    dia = sum(blob.count(c) for c in "ăâîșțĂÂÎȘȚ")
    if dia < 100: F(slug, f"doar {dia} diacritice in tot articolul, suspect de ASCII")

    # formulari negative
    for t in allt:
        for m in re.finditer(r"\b[Ff][ăa]r[ăa] (grij|bataie|băta|complica|stres|surpriz|problem)", t):
            W(slug, f"formulare negativa: ...{t[max(0,m.start()-30):m.end()+30]}...")

    # linkuri
    for t in allt:
        for href in re.findall(r'<a href="([^"]+)"', t):
            if href.startswith("/blog/"):
                s2 = href.strip("/").split("/")[-1]
                if href != "/blog/" and s2 not in KNOWN_BLOG:
                    F(slug, f"link catre slug de blog necunoscut: {href}")
            elif href.startswith("http"):
                W(slug, f"link extern in corp: {href}")
            elif href not in ALLOWED:
                F(slug, f"link intern nepermis: {href}")
    for r in p["readAlso"]:
        h=r["href"]
        if h.startswith("/blog/"):
            s2=h.strip("/").split("/")[-1]
            if s2 not in KNOWN_BLOG: F(slug, f"readAlso catre slug necunoscut: {h}")
        elif h not in ALLOWED: F(slug, f"readAlso nepermis: {h}")

    # structura
    if not (3 <= len(p["sections"]) <= 7): F(slug, f"{len(p['sections'])} sectiuni h2")
    if not (3 <= len(p["faq"]) <= 4): F(slug, f"{len(p['faq'])} intrebari FAQ")
    if len(p["readAlso"]) != 4: F(slug, f"{len(p['readAlso'])} intrari readAlso, cer exact 4")
    for b in [b for s in p["sections"] for b in s["blocks"]]:
        if b["t"] not in ("p","ul","h3"): F(slug, f"tip de bloc necunoscut: {b['t']}")
    # taguri permise
    for t in allt:
        for tag in re.findall(r"</?([a-zA-Z][a-zA-Z0-9]*)", t):
            if tag.lower() not in ("a","strong","em"): F(slug, f"tag nepermis <{tag}>")

    words = len(re.findall(r"\w+", " ".join(allt)))
    print(f"  {slug:36} seoTitle={lt:3}  desc={ld:3}  h2={len(p['sections'])}  faq={len(p['faq'])}  cuvinte~{words}")

print()
for w in warns: print("WARN ", w)
for f in fails: print("FAIL ", f)
print(f"\n=== {len(fails)} FAIL, {len(warns)} WARN ===")
sys.exit(1 if fails else 0)
