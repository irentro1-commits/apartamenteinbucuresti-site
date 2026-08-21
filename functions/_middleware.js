// COPIA DE PE `pages.dev` NU SE MAI INDEXEAZA.
//
// Andy, 21 aug 2026, dupa ce i-am aratat ce am gasit: "go pe toate".
//
// CE ERA. Cloudflare Pages serveste acelasi sit pe doua adrese: domeniul real si
// `apartamenteinbucuresti.pages.dev`. A doua raspundea `200`, cu `robots: index,follow` in
// pagina si acelasi `robots.txt` permisiv, deci Google avea in fata DOUA situri identice care
// spun amandoua ca sunt Ilioara Residence. E una dintre cauzele pentru care in rezultate apare
// domeniul in loc de numele proiectului: cand doua adrese revendica acelasi nume, motorul nu
// alege numele, alege ce e mai sigur, adica domeniul.
//
// DE CE NU AJUNGE `robots.txt`. `Disallow` opreste CITIREA, nu indexarea: o adresa blocata
// poate sta in continuare in rezultate, ca titlu gol, fiindca motorul stie ca exista din
// legaturi. Ca sa iasa, trebuie sa poata CITI pagina si sa gaseasca acolo `noindex`. Deci
// exact invers: se lasa citita si i se spune sa nu indexeze.
//
// DE CE UN ANTET SI NU O ETICHETA IN PAGINA. Fisierele sunt aceleasi pentru amandoua adresele,
// deci o eticheta pusa in HTML ar aparea si pe domeniul real. Antetul se poate pune conditionat
// de gazda, la servire. `X-Robots-Tag` face acelasi lucru ca eticheta, si pentru orice tip de
// fisier, nu doar pentru HTML.
//
// CE NU FACE: nu atinge domeniul real, nu schimba nimic din raspuns in afara antetului, si nu
// blocheaza pe nimeni. Daca lista de gazde de mai jos e goala sau gresita, situl ramane exact
// cum e: functia adauga un antet sau nu adauga nimic.

// Adresele pe care situl e EL INSUSI. Orice alta gazda serveste o copie.
const GAZDE_REALE = [
  "apartamenteinbucuresti.ro",
  "www.apartamenteinbucuresti.ro",
];

export async function onRequest(context) {
  const raspuns = await context.next();

  let gazda = "";
  try {
    gazda = new URL(context.request.url).hostname.toLowerCase();
  } catch (e) {
    return raspuns;               // adresa neasteptata: nu ne bagam
  }
  if (GAZDE_REALE.includes(gazda)) return raspuns;

  // orice altceva (pages.dev, previzualizari, adrese de test) iese din indexare
  const nou = new Response(raspuns.body, raspuns);
  nou.headers.set("X-Robots-Tag", "noindex, nofollow");
  return nou;
}
