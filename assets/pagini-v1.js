// reveal kinetic per element (IO per sectiune, P-K-03: nimic global, nimic pre-revelat sub fold)
(function(){
  if(matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var els = [].slice.call(document.querySelectorAll('.rv'));
  if(!('IntersectionObserver' in window)){ els.forEach(function(e){ e.classList.add('on'); }); return; }
  var io = new IntersectionObserver(function(entries){
    entries.forEach(function(en){
      if(en.isIntersecting){ en.target.classList.add('on'); io.unobserve(en.target); }
    });
  }, {threshold: .12, rootMargin: '0px 0px -4% 0px'});
  els.forEach(function(e){
    var r = e.getBoundingClientRect();
    if(r.top < innerHeight && r.bottom > 0){ e.classList.add('on'); io.unobserve(e); } // ce e deja in viewport apare direct
    else io.observe(e);
  });
})();
