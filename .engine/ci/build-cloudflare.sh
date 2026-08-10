#!/usr/bin/env bash
# Ce se PUBLICA pe Cloudflare Pages. Ruleaza in build-ul CF, nu la noi.
#
# Cloudflare Pages serveste si folderele care incep cu punct. Verificat pe live, 10 aug 2026:
# /.engine/README.md, /.engine/posts/ro/<slug>.json si /.github/workflows/*.yml raspundeau
# toate 200. Cat timp acolo stateau doar articole deja publicate, nu spunea nimic ce nu era
# deja pe site. Din clipa in care lotul de articole viitoare traieste in .engine/posts,
# **planul editorial pe o luna devine un URL public**, la o cale ghicibila, pentru oricine,
# inclusiv pentru un concurent activ pe acelasi proiect.
#
# Regula din _redirects nu ajuta: ea prinde doar caile inexistente, iar un fisier care exista
# in deployment castiga mereu. Singura solutie care chiar rezolva e ca fisierul sa NU AJUNGA
# in deployment. Asta face scriptul asta.
#
# Configurare in proiectul CF Pages (Settings -> Builds & deployments):
#     Build command:            bash .engine/ci/build-cloudflare.sh
#     Build output directory:   dist
#     Root directory:           /            (neschimbat)
#
# Daca scriptul pica, deployul pica, iar situl ramane pe versiunea buna anterioara.
set -euo pipefail

IESIRE="dist"
rm -rf "$IESIRE"
mkdir -p "$IESIRE"

# copiem tot, in afara de ce nu are ce cauta la vedere
tar --exclude="./$IESIRE" \
    --exclude="./.git" \
    --exclude="./.engine" \
    --exclude="./.github" \
    --exclude="./.secrets" \
    --exclude="./node_modules" \
    -cf - . | (cd "$IESIRE" && tar -xf -)

# Fisierele de platforma TREBUIE sa fie in radacina iesirii, altfel Cloudflare nu le vede
# si pierzi tacut headerele de securitate si redirectarile. Se verifica, nu se presupune.
for f in _headers _redirects robots.txt sitemap.xml sitemap-index.xml llms.txt; do
  if [ -f "$f" ] && [ ! -f "$IESIRE/$f" ]; then
    echo "FAIL: $f lipseste din $IESIRE" >&2
    exit 1
  fi
done

# si invers: ce nu trebuie sa ajunga public, chiar nu a ajuns
for d in .engine .github .secrets .git; do
  if [ -e "$IESIRE/$d" ]; then
    echo "FAIL: $d a ajuns in $IESIRE" >&2
    exit 1
  fi
done

echo "dist: $(find "$IESIRE" -name index.html | wc -l) pagini, $(du -sh "$IESIRE" | cut -f1)"
