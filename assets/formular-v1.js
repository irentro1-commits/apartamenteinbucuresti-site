/* Trimiterea formularului, fara sa plece pagina de sub picioarele omului.
   Fara JS, formularul tot merge: <form> are action si method, iar CSP lasa form-action spre
   endpoint. Cu JS, omul ramane pe pagina si vede raspunsul pe loc. */
(function () {
  "use strict";
  var forme = document.querySelectorAll("form.lf-f");
  if (!forme.length) return;

  Array.prototype.forEach.call(forme, function (f) {
    if (f.dataset.lfGata === "1") return;
    f.dataset.lfGata = "1";

    var radacina = f.closest(".lf") || f.parentNode;
    var ok = radacina.querySelector(".lf-ok");
    var ero = radacina.querySelector(".lf-ero");
    var btn = f.querySelector(".lf-b");
    var textBtn = btn ? btn.textContent : "";
    var textTrimit = (btn && btn.dataset.trimit) || textBtn;

    f.addEventListener("submit", function (e) {
      if (!f.checkValidity()) return; /* lasam browserul sa arate mesajele native */
      e.preventDefault();
      if (btn) { btn.disabled = true; btn.textContent = textTrimit; }
      if (ero) ero.classList.remove("on");

      fetch(f.action, {
        method: "POST",
        headers: { Accept: "application/json" },
        body: new FormData(f)
      })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d && d.success) {
            f.classList.add("off");
            if (ok) ok.classList.add("on");
          } else {
            throw new Error("raspuns fara success");
          }
        })
        .catch(function () {
          if (ero) ero.classList.add("on");
          if (btn) { btn.disabled = false; btn.textContent = textBtn; }
        });
    });
  });
})();
