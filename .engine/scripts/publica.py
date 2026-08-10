#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PUBLICAREA. Un singur punct de intrare, si singurul care are voie sa scrie in repo.

    python3 publica.py --repo /tmp/apt                 # publicarea de azi
    python3 publica.py --repo /tmp/apt --azi 2026-09-01  # ceas fals, pentru probe
    python3 publica.py --repo /tmp/apt --tot           # si articolele inca nepublicate

MODELUL, luat de la omdetreaba.ro: **publicarea e o DATA, nu un cron.** Articolele se scriu
toate odata, fiecare cu `publishAt`-ul lui, si intra pe site singure cand le vine ziua.
Nimic nu depinde de un laptop pornit la ora sase dimineata.

Diferenta fata de omdetreaba: acolo paginile sunt dinamice pe edge, deci filtrarea se face
la fiecare cerere. Aici situl e HTML static, deci filtrarea se face la BUILD, iar buildul il
porneste un cron zilnic din GitHub Actions. Efectul pentru cititor e identic; efectul pentru
noi e ca ziua publicarii se vede intr-un comit, deci exista dovada.

ORDINEA PASILOR NU E ARBITRARA:
  1. valideaza datele        gate pe JSON, INAINTE sa se scrie un octet de HTML
  2. build_blog              paginile de articol, doar cele cu publishAt trecut
  3. build_index             indexul blogului, in 5 limbi
  4. pas_dif                 blocul de canale de vanzare (post-generare)
  5. pas_asezare             legaturile nedespartitoare (post-generare, ULTIMUL pas pe text)
  6. update_index_files      sitemap.xml, sitemap-index.xml, llms.txt

Pasii 4 si 5 exista fiindca pe 4 aug 2026 au fost facuti cu scripturi one-shot din /tmp, iar
sursa n-a stiut niciodata de ei. Rezultat: pe 10 aug, o regenerare din JSON stergea 91 de
spatii nedespartitoare si tot blocul de canale, de pe fiecare pagina, in cinci limbi.
**Un pas care atinge HTML-ul generat si NU e in pipeline e o bomba cu ceas.**
Verificarea care tine legea asta in viata: `verifica_fidelitate.py`.

pas_asezare vine ULTIMUL fiindca leaga cuvinte din textul FINAL. Orice pas care mai schimba
text dupa el lasa in urma legaturi puse pe fraze care nu mai exista.
"""
import argparse, json, os, subprocess, sys, glob

ENGINE = os.path.dirname(os.path.abspath(__file__))
LANGS = ["ro", "en", "he", "ar", "uk"]
BLOG_GLOB = "**/blog/**/index.html"


def ruleaza(cmd, mediu):
    r = subprocess.run(cmd, cwd=ENGINE, env=mediu, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr, file=sys.stderr)
        raise SystemExit(f"FAIL la pasul: {' '.join(cmd[1:3])}")
    return r.stdout.rstrip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("BLOG_REPO", "/tmp/apt"))
    ap.add_argument("--posts", default=None)
    ap.add_argument("--azi", default=None, help="ceas fals: AAAA-LL-ZZ")
    ap.add_argument("--tot", action="store_true", help="scrie si articolele nepublicate")
    a = ap.parse_args()

    sys.path.insert(0, ENGINE)
    import build_blog as bb
    azi = a.azi or bb.azi_ro()
    posts = a.posts or os.path.join(os.path.dirname(ENGINE), "posts")
    mediu = dict(os.environ, BLOG_REPO=a.repo, BLOG_POSTS=posts)

    print(f"PUBLICARE  repo={a.repo}  ceas={azi}" + ("  (TOT)" if a.tot else ""))

    print("\n1. gate pe date")
    for l in LANGS:
        print(ruleaza(["python3", "validate_posts.py", "--posts", os.path.join(posts, l)], mediu))

    print("\n2. paginile de articol")
    for l in LANGS:
        cmd = ["python3", "build_blog.py", "--repo", a.repo,
               "--posts", os.path.join(posts, l), "--lang", l, "--azi", azi]
        if a.tot:
            cmd.append("--tot")
        out = ruleaza(cmd, mediu)
        print(f"  {l}: {out.splitlines()[-1]}")

    print("\n3. indexul blogului")
    print(ruleaza(["python3", "build_index.py", azi], mediu))

    print("\n4. blocul de canale de vanzare")
    print(ruleaza(["python3", "pas_dif.py", "--repo", a.repo,
                   "--doar", BLOG_GLOB, "--apply"], mediu))

    print("\n5. asezarea textului")
    print(ruleaza(["python3", "pas_asezare.py", "--repo", a.repo,
                   "--doar", BLOG_GLOB, "--apply"], mediu))

    print("\n6. sitemap + llms.txt")
    print(ruleaza(["python3", "update_index_files.py", azi], mediu))

    # raportul: ce e pe site si ce urmeaza. Serveste si workflow-ului, ca sa stie ce sa scrie
    # in mesajul de comit, si mie, ca sa vad dintr-o privire daca coada mai are combustibil.
    print("\n" + "-" * 68)
    azi_pub, coada = [], []
    for fp in sorted(glob.glob(os.path.join(posts, "ro", "*.json"))):
        p = json.load(open(fp, encoding="utf-8"))
        d = bb.data_pub(p)
        (azi_pub if d == azi else coada if d > azi else []).append((d, p["slug"]))
    for d, s in sorted(azi_pub):
        print(f"APARE AZI   {d}  {s}")
    for d, s in sorted(coada)[:6]:
        print(f"la rand     {d}  {s}")
    if len(coada) > 6:
        print(f"            ... inca {len(coada) - 6}")
    if not coada:
        print("COADA GOALA. Dupa ce iese ce e azi, blogul nu mai creste singur.")
    print("-" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
