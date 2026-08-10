#!/usr/bin/env python3
"""Gate pe batch-ul de articole (blog-seo). Exit 1 la FAIL."""
import argparse, json, re, sys, glob, os, unicodedata

AP = argparse.ArgumentParser()
AP.add_argument("--posts", default=os.environ.get("BLOG_POSTS_LANG", "/tmp/posts"))
ARGS, _ = AP.parse_known_args()

ALLOWED = {
 "/", "/apartamente/", "/preturi/", "/dotari/", "/credit-ipotecar/", "/zona/",
 "/parcare/", "/proiecte-finalizate/", "/pentru-cine-construim/",
 "/echipa-ilioara-residence/", "/blog/", "/informatii-legale/",
 "/apartamente-noi-bucuresti/", "/blocuri-noi-bucuresti/",
 "/apartamente-blocuri-noi-bucuresti/",
}
# Slugurile cunoscute se CITESC din folder, nu se scriu cu mana. Lista scrisa cu mana
# ramane in urma la primul articol nou si incepe sa dea FAIL pe legaturi perfect valide,
# adica exact genul de gate pe care oamenii invata sa-l ignore.
KNOWN_BLOG = {os.path.basename(f)[:-5] for f in glob.glob(os.path.join(ARGS.posts, "*.json"))}
REQ = ["slug","publishAt","title","seoTitle","description","descriptionLlm","articleSection",
       "keywords","readMinutes","lead","sections","faq","ctaAfter","readAlso"]
DATA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# `sablon` separa doua feluri de articol, si separarea e explicita in fisier, nu ghicita
# dupa data. "ghid" = scris pe sablonul de acum, deci trece prin toate pragurile de structura.
# "vechi" = cele sase articole de proiect, scoase in JSON din HTML scris de mana inainte sa
# existe sablonul. Pragurile de STRUCTURA devin avertisment pentru ele, fiindca sunt live si
# corecte asa; pragurile de CONTINUT (diacritice, deschideri de robot, liniute, cedila,
# legaturi moarte) raman blocante pentru toata lumea. Un gate care da FAIL pe ceva ce nu are
# nimeni de gand sa schimbe e un gate pe care oamenii invata sa-l ignore, si atunci nu mai
# prinde nici ce conteaza.
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

files = sorted(glob.glob(os.path.join(ARGS.posts, "*.json")))
if not files: print(f"ZERO fisiere in {ARGS.posts}"); sys.exit(1)

# datele de publicare ale tuturor articolelor din limba asta, pentru verificarea legaturilor
DATE_PUB = {}
for _f in files:
    _p = json.load(open(_f, encoding="utf-8"))
    DATE_PUB[_p.get("slug","?")] = _p.get("publishAt") or _p.get("publishedAt") or ""
print(f"Validez {len(files)} articole\n")

for fp in files:
    p = json.load(open(fp, encoding="utf-8"))
    slug = p.get("slug","?")
    strict = p.get("sablon", "ghid") == "ghid"
    S = F if strict else W          # pragurile de structura, blocante doar pe sablonul nou
    for k in REQ:
        if k not in p: F(slug, f"lipseste cheia '{k}'")
    if os.path.basename(fp) != slug + ".json":
        F(slug, f"numele fisierului nu se potriveste cu slug")

    # datele
    for k in ("publishAt", "updatedAt"):
        v = p.get(k)
        if v is not None and not DATA_RE.match(str(v)):
            F(slug, f"{k} = {v!r}, cer forma AAAA-LL-ZZ")
    if p.get("updatedAt") and p.get("publishAt") and p["updatedAt"] < p["publishAt"]:
        F(slug, f"updatedAt {p['updatedAt']} inainte de publishAt {p['publishAt']}")

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
    # Interdictia de liniuta e o regula de VOCE romaneasca si engleza, nu o lege universala.
    # In ucraineana tire e punctuatie obligatorie ("Стандартна ставка — 21%"), la fel ca virgula:
    # scoasa, propozitia devine gresita gramatical. Gate-ul dadea 11 FAIL pe traduceri corecte,
    # adica exact zgomotul care il invata pe om sa treaca peste toate FAIL-urile deodata.
    if os.path.basename(os.path.normpath(ARGS.posts)) not in ("uk",):
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

    # DIACRITICE, masurate ca PROPORTIE, nu ca numar absolut. Pragul vechi era "sub 100
    # de diacritice in tot articolul", si asta masoara lungimea, nu corectitudinea: un articol
    # scurt si perfect scris pica, iar unul lung si pe jumatate ciuntit trece. Proza romaneasca
    # reala are intre 3,5% si 5,5% diacritice din caractere; sub 1,5% inseamna text scris fara.
    # Asa a fost prins, pe 10 aug 2026, `apartamente-noi-titan-dristor`: 0,15%, adica romana
    # fara nicio diacritica, LIVE de doua luni, pe o pagina de cuvant-cheie. Vechiul prag il
    # semnala si el, dar cu un mesaj despre "agent care a returnat ASCII", deci suna a
    # problema de unealta, nu a text de reparat, si nimeni nu s-a dus sa se uite.
    if os.path.basename(os.path.normpath(ARGS.posts)) == "ro":
        dia = sum(blob.count(c) for c in "ăâîșțĂÂÎȘȚ")
        rap = 100.0 * dia / max(1, len(blob))
        if rap < 1.5:
            F(slug, f"{rap:.2f}% diacritice: textul romanesc e scris FARA diacritice")
        elif rap < 2.8:
            W(slug, f"{rap:.2f}% diacritice, sub proza romaneasca obisnuita (3,5-5,5%)")

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
            # Legatura catre un articol care apare MAI TARZIU: avertisment, nu oprire.
            # Generatorul o scoate singur pana cand tinta exista, si o pune inapoi automat
            # in ziua in care tinta se publica, fiindca rularea zilnica regenereaza tot ce e
            # publicat. Asa se poate scrie graful de legaturi interne DIN PRIMA, cu lotul
            # intreg in fata, si se completeaza singur pe masura ce ies articolele.
            # FAIL ar fi fost gresit aici: ar interzice exact planificarea care da valoare.
            elif DATE_PUB.get(s2, "") > p.get("publishAt", ""):
                W(slug, f"readAlso catre {s2} apare abia pe {DATE_PUB[s2]}: legatura sta "
                        f"ascunsa pana atunci, apoi intra singura")
        elif h not in ALLOWED: F(slug, f"readAlso nepermis: {h}")

    # structura
    if not (3 <= len(p["sections"]) <= 7): S(slug, f"{len(p['sections'])} sectiuni h2")
    if not (3 <= len(p["faq"]) <= 4): S(slug, f"{len(p['faq'])} intrebari FAQ")
    if len(p["readAlso"]) != 4: S(slug, f"{len(p['readAlso'])} intrari readAlso, cer exact 4")
    for b in [b for s in p["sections"] for b in s["blocks"]]:
        if b["t"] not in ("p","ul","h3"): F(slug, f"tip de bloc necunoscut: {b['t']}")
    # taguri permise
    for t in allt:
        for tag in re.findall(r"</?([a-zA-Z][a-zA-Z0-9]*)", t):
            if tag.lower() not in ("a","strong","em","b","br"): F(slug, f"tag nepermis <{tag}>")

    words = len(re.findall(r"\w+", " ".join(allt)))
    print(f"  {slug:36} seoTitle={lt:3}  desc={ld:3}  h2={len(p['sections'])}  faq={len(p['faq'])}  cuvinte~{words}")

print()
for w in warns: print("WARN ", w)
for f in fails: print("FAIL ", f)
print(f"\n=== {len(fails)} FAIL, {len(warns)} WARN ===")
sys.exit(1 if fails else 0)
