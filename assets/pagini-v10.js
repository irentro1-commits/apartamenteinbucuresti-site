// meniul respira cu scrollul (cerinta Andy): in jos dispare, in sus apare; sus de tot e mereu vizibil
(function(){
  var h = document.querySelector('.ph');
  if(!h) return;
  var last = scrollY, acc = 0;
  addEventListener('scroll', function(){
    var y = scrollY, d = y - last; last = y;
    if(document.body.classList.contains('mn-open')) return;
    if(y < 80){ h.classList.remove('hide'); document.body.classList.remove('hdr-hidden'); acc = 0; return; }
    acc = (d > 0) === (acc > 0) ? acc + d : d;
    if(acc > 90){ h.classList.add('hide'); document.body.classList.add('hdr-hidden'); }
    else if(acc < -50){ h.classList.remove('hide'); document.body.classList.remove('hdr-hidden'); }
  }, {passive:true});
})();
// meniul: mereu accesibil (butoanele din bara + cel plutitor deschid acelasi panou)
(function(){
  var btns = [].slice.call(document.querySelectorAll('.mn-btn'));
  if(!btns.length) return;
  function setMn(open){
    document.body.classList.toggle('mn-open', open);
    btns.forEach(function(b){ b.setAttribute('aria-expanded', open ? 'true' : 'false'); });
  }
  btns.forEach(function(b){ b.addEventListener('click', function(){ setMn(!document.body.classList.contains('mn-open')); }); });
  [].slice.call(document.querySelectorAll('.mn-panel a')).forEach(function(a){
    a.addEventListener('click', function(){ setMn(false); });
  });
  addEventListener('keydown', function(e){
    if(e.key === 'Escape' && document.body.classList.contains('mn-open')) setMn(false);
  });
})();
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
