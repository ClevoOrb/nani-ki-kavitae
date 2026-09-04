/* Blossoms and syllables lifting off the page beside the poet.
   Two kinds of drifting thing:
     · letters  — Devanagari vowels, set in the verse face so they always render
     · blooms   — drawn in CSS, so they never depend on a font having a flower glyph
*/
(function () {
  "use strict";
  var host = document.getElementById("petals");
  if (!host) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var LETTERS = ["अ", "आ", "ई", "म", "न", "स", "प", "ऐ", "ओ", "र"];
  var TINTS = ["--coral-deep", "--marigold-deep", "--mint-deep",
              "--sky-deep", "--lilac-deep", "--rose-deep"];
  // a phone-sized column cannot carry as many without looking littered
  var TOTAL = host.offsetWidth < 520 ? 8 : 15;

  // how far a bloom must travel to clear the column — a % would resolve
  // against the petal's own tiny box, so this is measured in px.
  var rise = Math.max(host.offsetHeight, 460) * 1.15;

  function place(el, i) {
    var dur = 12 + Math.random() * 13;              // slow and unhurried
    var side = i % 2 ? 1 : 0;                        // alternate edges
    el.style.left = (side ? 62 + Math.random() * 34
                          :  1 + Math.random() * 26) + "%";
    el.style.animationDuration = dur + "s";
    el.style.animationDelay = (-Math.random() * dur) + "s";
    el.style.setProperty("--dx", (Math.random() * 130 - 65) + "px");
    el.style.setProperty("--ry", -(rise + Math.random() * 80) + "px");
    // blooms may tumble freely; a syllable has to stay readable
    var spin = el.classList.contains("letter") ? 16 : 210;
    el.style.setProperty("--rot", (Math.random() * spin * 2 - spin) + "deg");
    el.style.color = "var(" + TINTS[i % TINTS.length] + ")";
    host.appendChild(el);
  }

  for (var i = 0; i < TOTAL; i++) {
    var el = document.createElement("span");
    if (i % 2 === 0) {                               // a syllable
      el.className = "petal letter";
      el.textContent = LETTERS[i % LETTERS.length];
      el.style.fontSize = (1.5 + Math.random() * 1.5) + "rem";
    } else {                                         // a bloom
      el.className = "petal bloom";
      var d = 10 + Math.random() * 13;
      el.style.width = d + "px";
      el.style.height = d + "px";
    }
    place(el, i);
  }

  /* Pause the banner's motion once it has scrolled out of sight, and the
     lamp on the dedication card until that card is on screen. Identical
     appearance whenever they are visible; simply no work when they are not. */
  if (window.IntersectionObserver) {
    var pairs = [[document.querySelector(".hero"), "hero-idle"],
                 [document.querySelector(".gift"), "gift-idle"]];
    pairs.forEach(function (pr) {
      if (!pr[0]) return;
      new IntersectionObserver(function (es) {
        es.forEach(function (e) {
          document.body.classList.toggle(pr[1], !e.isIntersecting);
        });
      }, { rootMargin: "80px" }).observe(pr[0]);
    });
  }
})();
