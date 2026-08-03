# Motorul de blog, apartamenteinbucuresti.ro

Un articol pe zi, in cinci limbi, dintr-o singura sursa de date.

**Coada de subiecte NU e aici.** Traieste pe calculatorul lui Andy, la `_websites/_blog-engine/coada.json`, si se aduce cu `device_stage_files` la inceputul rutinei. Motivul, platit pe 4 august 2026: Cloudflare Pages SERVESTE si folderele care incep cu punct, iar un fisier care exista in repo castiga in fata regulii din `_redirects`, care prinde doar caile inexistente. Scripturile si articolele deja publicate pot sta linistite aici, nu spun nimic ce nu e deja pe site. Planul urmatoarei luni de articole nu are ce cauta la vedere, cu un concurent activ pe acelasi proiect.

## Ce e aici

```
.engine/
  posts/
    ordine.json        ordinea cardurilor pe pagina de index, primul = cel mai sus
    index-strings.json sirurile paginii de index in en, he, ar, uk
    ro/ en/ he/ ar/ uk/ cate un JSON per articol per limba
  scripts/
    build_blog.py         genereaza paginile de articol dintr-un folder de JSON
    build_index.py        genereaza pagina de index a blogului in toate cele 5 limbi
    update_index_files.py rescrie sitemap.xml, sitemap-index.xml si sectiunea de blog din llms.txt
    validate_posts.py     gate pe datele JSON, INAINTE de generare
    check_pages.py        gate pe HTML-ul generat
    extract_posts.py      intoarce un articol HTML existent inapoi in JSON, daca vreodata se pierde sursa
```

Continutul traieste in JSON, niciodata direct in HTML. Coaja paginii (head, meniu, footer, scripturi) se ia la fiecare rulare dintr-o pagina reala din repo, deci orice schimbare de design a site-ului intra automat in articolele regenerate.

## Rutina zilnica

Se ruleaza dintr-o clona proaspata in `/tmp`, niciodata de pe mount.

```bash
git clone https://github.com/irentro1-commits/apartamenteinbucuresti-site.git /tmp/apt
cd /tmp/apt/.engine/scripts
export BLOG_REPO=/tmp/apt BLOG_POSTS=/tmp/apt/.engine/posts
```

1. **Alege subiectul.** Adu coada de pe calculatorul lui Andy (`_websites/_blog-engine/coada.json`) si ia primul element cu `"stare": "liber"`. Citeste unghiul si linkurile lui.
2. **Verifica faptele.** Orice cifra din afara listei de fapte ale proiectului se cauta pe sursa primara si se trece in campul `sources` al articolului. Legislatia fiscala se re-verifica la fiecare articol care o atinge, chiar daca alt articol o are deja scrisa: cotele si termenele se schimba.
3. **Scrie articolul in romana** ca JSON in `posts/ro/<slug>.json`, dupa forma oricarui fisier existent de acolo. Regulile de voce sunt mai jos.
4. **Ruleaza gate-ul pe date:** `python3 validate_posts.py` cu folderul `posts/ro`. Zero FAIL inainte sa mergi mai departe.
5. **Tradu** in en, he, ar, uk, cate un fisier in fiecare folder, cu aceleasi chei, acelasi numar de blocuri si **aceleasi hrefuri in forma romaneasca**. Prefixul de limba se pune automat la generare.
6. **Adauga slugul in `posts/ordine.json`**, pe pozitia unde vrei sa apara cardul (de obicei primul).
7. **Genereaza:**
   ```bash
   for l in ro en he ar uk; do python3 build_blog.py --repo $BLOG_REPO --posts $BLOG_POSTS/$l --lang $l; done
   python3 build_index.py $(TZ='Europe/Bucharest' date +%F)
   python3 update_index_files.py $(TZ='Europe/Bucharest' date +%F)
   ```
8. **Gate pe HTML:** `python3 check_pages.py` pe paginile noi. Apoi randeaza local si uita-te cu ochii, pe mobil si pe o pagina RTL:
   ```bash
   cd $BLOG_REPO && python3 -m http.server 8899 &
   ```
   Chromium din sandbox nu are iesire la internet, deci taie orice request care nu e catre 127.0.0.1.
9. **Marcheaza in coada** `"stare": "publicat"`, adauga `"data": "AAAA-LL-ZZ"`, si scrie fisierul inapoi pe calculatorul lui Andy cu `device_commit_files`. Coada nu se comite niciodata in repo.
10. **Un singur commit**, cu toate fisierele. Cloudflare Pages deployeaza serial, deci comiturile in rafala intarzie live-ul cu minute bune.
11. **Dupa ce confirmi pe live**, pinguieste IndexNow (comanda mai jos).

## Reguli de voce, neschimbate

Romana cu diacritice complete, cu virgula dedesubt: ă â î ș ț. Niciodata cedila ş ţ.
Zero liniuta lunga si zero liniuta scurta folosita ca legatura intre propozitii, in romana si in engleza. In ucraineana tirele sunt punctuatie obligatorie si se folosesc normal.
Zero formulare negativa de tip "fara X". Se reformuleaza pozitiv.
Zero deschidere de robot: Desigur, Absolut, Iată, În concluzie, Este important de menționat.
Deschiderea e un scenariu concret pe care cititorul il vede, niciodata o definitie.
Ritmul scurt-paradox, de doua pana la patru ori: doua propozitii scurte care resping o presupunere si o inlocuiesc.
Onestitatea despre limitari vine inaintea oricarui indemn la actiune.
Zero cifra inventata. Pe onorarii, dobanzi si preturi de piata se scrie mecanismul, nu suma.
Pilon 1100 pana la 1600 de cuvinte, cluster 700 pana la 1000. Fiecare cluster linkeaza in sus catre pilonul lui.

## Faptele proiectului, singurele cifre care se folosesc fara sursa externa

Ilioara Residence, Aleea Eprubetei 7-11, Titan-Dristor, Sector 3, Bucuresti. Parter plus 8 etaje, 33 de apartamente, 4 pe etaj, strada inchisa. Finalizare decembrie 2026.
Preturi fara TVA: 2 camere intre 107.500 si 136.500 EUR, 3 camere intre 151.000 si 168.000 EUR. Parcare simpla 20.000 EUR, dubla tip Klauss 25.000 EUR. Rezervare 2.000 EUR. Avans minim 30%.
Cota de TVA aplicabila la Ilioara: 21%, cota standard din Romania de la 1 august 2025 prin Legea 141/2025. Livrarea in decembrie 2026 cade dupa termenul regimului tranzitoriu de 9%, deci cota redusa nu se poate aplica aici.
Dotari incluse: incalzire in pardoseala peste tot, inclusiv pe balcon; tamplarie tripan Salamander cu 7 camere; centrala proprie Ariston de 24 kW; compartimentare modulara.
Distante pe jos: metrou Nicolae Grigorescu 5 minute, autobuz Ilioara 3 minute, tramvaiele 19, 23 si 27 la 4 minute, parcul IOR 9 minute, ParkLake 15 minute, metrou Titan 18 minute.
Vanzare directa de la proprietari, zero comision pentru cumparator. Contact WhatsApp 0774 096 700.

Disponibilitatea (12 din 33) se schimba. Se confirma cu Andy inainte sa apara intr-un articol nou.

## Capcane de repo

`/assets/*`, `/fonts/*` si `/film2/*` au cache immutable un an: un fisier modificat primeste NUME NOU de versiune, niciodata editat pe loc. Blogul nu atinge assets, deci nu apare problema, dar daca vreodata schimbi `pagini-vN.css`, bumpul e obligatoriu.
HTML-ul e `max-age=0, must-revalidate`, deci se updateaza imediat dupa deploy.
CSP e enforce. Un script extern nou cere domeniul in `script-src` din `_headers`.
Verificarea structurala nu prinde bugurile de cascada CSS. Se randeaza local si se priveste, mai ales o pagina RTL.

## IndexNow

Cheia e la `/3b82c83e09f7e6727f43d556d6225e25.txt`. Dupa ce confirmi ca URL-urile noi raspund 200 pe live:

```bash
curl -sS -X POST https://api.indexnow.org/IndexNow \
  -H 'Content-Type: application/json' \
  -d '{"host":"apartamenteinbucuresti.ro",
       "key":"3b82c83e09f7e6727f43d556d6225e25",
       "keyLocation":"https://apartamenteinbucuresti.ro/3b82c83e09f7e6727f43d556d6225e25.txt",
       "urlList":["https://apartamenteinbucuresti.ro/blog/SLUG/", "..."]}'
```

Raspuns 200 sau 202 inseamna acceptat.

## Push

PAT-ul se citeste inline din `.secrets/github-pat.txt` de pe mountul lui Andy, niciodata afisat.

```bash
git -c http.extraHeader="Authorization: Basic $(printf 'x-access-token:%s' "$(cat /mnt/user-data/uploads/_websites/.secrets/github-pat.txt)" | base64 -w0)" push origin main
```

Dupa push: `git ls-remote origin main` confirma hashul, apoi `curl` pe live. Live-ul poate intarzia din coada de deploy, asta nu e bug.

## Log

Dupa fiecare publicare, o intrare in `_LOGS/apartamenteinbucuresti-log.md` de pe mountul lui Andy: ce s-a publicat, pe ce cuvinte, ce s-a verificat si cu ce sursa, si orice a picat la gate. Verify clock cu `TZ='Europe/Bucharest' date` inainte de orice data scrisa.
