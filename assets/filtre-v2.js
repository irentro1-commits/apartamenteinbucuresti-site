/* FILTRELE listei de apartamente: taburi pe numarul de camere si comutator "doar disponibile".
   Merge pe orice container marcat cu `data-filtrabil`, deci si pe /apartamente/, si pe /preturi/.

   DE CE E FISIER SEPARAT, si e o lectie platita pe 21 aug 2026. Codul asta a fost intai INLINE,
   injectat la sfarsitul paginii de generator. Cand randurile s-au redenumit din `.card` in
   `.aprow`, generatorul a vazut ca in pagina exista deja un bloc de filtrare si nu l-a mai
   inlocuit: pagina a ramas cu un script care cauta elemente care nu mai existau. Efectul, pe
   LIVE: comutatorul "doar disponibile" ascundea TOT si scria "nu e niciun apartament", desi
   erau sapte. Un fisier extern nu are problema asta: pagina il refera, si continutul lui e
   intotdeauna cel de acum.

   Elementele se cauta dupa `data-stare` si `data-cam`, nu dupa numele clasei, tocmai ca o
   redenumire de clasa sa nu mai poata rupe filtrarea a doua oara. */
(function () {
  "use strict";
  var containere = [].slice.call(document.querySelectorAll("[data-filtrabil]"));
  if (!containere.length) return;

  /* ASCUNDEREA SE FACE PE `style.display`, NU PE ATRIBUTUL `hidden`.
     `hidden` e doar `display:none` cu specificitate zero, deci ORICE regula de layout il bate.
     Pe /preturi/ randurile au `display:grid` din foaia de stil, asa ca `hidden` nu avea niciun
     efect: comutatorul "doar disponibile" parea sa mearga, dar rezervatele ramaneau pe ecran.
     Numarul de deasupra spunea 7 si dedesubt se vedeau 12. Un stil in linie nu poate fi batut
     de nicio foaie, deci filtrul merge pe orice element, indiferent cum e stilizat. */
  function arata(el, da) {
    el.style.display = da ? "" : "none";
  }

  containere.forEach(function (lista) {
    var bara = document.querySelector('[data-filtre-pentru="' + lista.id + '"]') ||
               document.getElementById("filtre");
    if (!bara) return;

    var taburi = [].slice.call(bara.querySelectorAll(".ft"));
    var comutator = bara.querySelector('input[type="checkbox"]');
    var gol = document.getElementById(lista.id + "-gol") || document.getElementById("f-gol");

    function aplica() {
      var cam = lista.getAttribute("data-f-cam") || "toate";
      var doarLibere = lista.getAttribute("data-f-lib") === "1";
      var vazute = 0;

      [].forEach.call(lista.querySelectorAll("[data-stare]"), function (r) {
        var potrivit =
          (cam === "toate" || r.getAttribute("data-cam") === cam) &&
          (!doarLibere || r.getAttribute("data-stare") === "disponibil");
        arata(r, potrivit);
        if (potrivit) vazute++;
      });

      // o sectiune fara niciun rand vizibil nu are ce cauta pe ecran, cu titlu cu tot
      [].forEach.call(lista.querySelectorAll("[data-sectiune]"), function (s) {
        var areRanduri = false;
        [].forEach.call(s.querySelectorAll("[data-stare]"), function (r) {
          if (r.style.display !== "none") areRanduri = true;
        });
        arata(s, areRanduri);
      });

      if (gol) gol.hidden = vazute > 0;
    }

    taburi.forEach(function (b) {
      b.addEventListener("click", function () {
        taburi.forEach(function (x) {
          x.classList.remove("on");
          x.setAttribute("aria-pressed", "false");
        });
        b.classList.add("on");
        b.setAttribute("aria-pressed", "true");
        lista.setAttribute("data-f-cam", b.getAttribute("data-cam"));
        aplica();
      });
    });

    if (comutator) {
      comutator.addEventListener("change", function () {
        lista.setAttribute("data-f-lib", comutator.checked ? "1" : "0");
        aplica();
      });
    }
  });
})();
