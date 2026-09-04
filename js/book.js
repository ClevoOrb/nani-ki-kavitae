/* ==========================================================================
   उन्मुक्त मन — book engine
   Page fragments are fetched with htmx and cached; the turn itself is a
   CSS 3D rotation of a single leaf element that is reused for every flip.
   ========================================================================== */
(function () {
  "use strict";

  var PAGES = [];        // [{id, kind, printed, heading, section, title}]
  var TOC = [];          // [{title, tint, start, items:[{title, index, printed}]}]
  var VERSION = "";      // fragment build stamp, used to bust stale caches
  var warmed = new Set();// page indices already pulled into the HTTP cache
  var idx = 0;           // index of the page shown on the RIGHT half
  var part = 0;          // which part of that page, when it is split for a phone
  var busy = false;
  var mode = "spread";

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var book, leftHalf, rightHalf, leaf, leafFront, leafBack;

  /* ---------- data ------------------------------------------------------ */
  // VERSION changes whenever the fragments are rebuilt, so a new build is
  // never hidden behind a cached copy of the old page.
  function fragUrl(i) {
    return "fragments/" + PAGES[i].id + ".html" + (VERSION ? "?v=" + VERSION : "");
  }

  /* Every page surface is filled by htmx, so each leaf face and each half of
     the spread is a real hx-swap target rather than hand-built innerHTML. */
  /* ---------- splitting a dense page on a small screen -------------------
     A phone leaf cannot hold the longest poems at a readable size, and
     shrinking the type to fit makes every page a different size. Instead the
     verse is dealt out over as many parts as it needs, each filled to the
     page at the SAME type size, so reading is uniform. Page indices are left
     alone — the cursor becomes (page, part) — so the contents, the slider and
     the #p48 links keep working untouched. */
  var PARTS = new Map();
  var partsKey = "";
  var measureEl = null;

  function measureHost() {
    if (!measureEl) {
      measureEl = document.createElement("div");
      measureEl.className = "half";
      measureEl.setAttribute("aria-hidden", "true");
      measureEl.style.cssText = "left:-99999px;top:0;visibility:hidden;pointer-events:none";
      book.appendChild(measureEl);
    }
    return measureEl;
  }

  function partsCacheKey() {
    var cs = getComputedStyle(document.documentElement);
    return (isSingle() ? "s" : "d") + cs.getPropertyValue("--leaf-w") + cs.getPropertyValue("--leaf-h");
  }

  function buildParts(html) {
    var host = measureHost();
    host.innerHTML = html;
    var page = host.firstElementChild;
    if (!page) return [html];
    var body = page.querySelector(".verse, .prose");

    // The contents pages carry no running text — they are a grid of sections.
    var cols = page.querySelector(".toc-cols");
    if (!body && cols) return splitBlocks(page, cols);
    if (!body) return [html];

    var prose = body.classList.contains("prose");
    var glue = prose ? "" : "\n";
    function fits(arr) {
      body.innerHTML = arr.join(glue);
      return body.scrollHeight <= body.clientHeight + 1;
    }

    var units = prose
      ? Array.prototype.map.call(body.children, function (n) { return n.outerHTML; })
      : body.innerHTML.replace(/^\n+|\n+$/g, "").split("\n");

    // A single paragraph can be taller than the leaf on its own; break it at
    // sentence ends so it can still be dealt out.
    if (prose) {
      var expanded = [];
      units.forEach(function (u) {
        if (fits([u])) { expanded.push(u); return; }
        var inner = u.replace(/^<p[^>]*>|<\/p>$/g, "");
        var sentences = inner.split(/(?<=।)\s+/);
        var buf = "";
        sentences.forEach(function (sn) {
          var trial = buf ? buf + " " + sn : sn;
          if (buf && !fits(["<p>" + trial + "</p>"])) { expanded.push("<p>" + buf + "</p>"); buf = sn; }
          else { buf = trial; }
        });
        if (buf) expanded.push("<p>" + buf + "</p>");
      });
      units = expanded;
    }

    if (fits(units)) { body.innerHTML = units.join(glue); return [page.outerHTML]; }

    // Adding one unit at a time meant one forced layout per line. Whether a
    // prefix fits is monotonic, so the same boundary — the longest prefix that
    // fits — is found by bisection in log2(n) measurements instead of n.
    var chunks = [], start = 0;
    while (start < units.length) {
      var lo = 1, hi = units.length - start, best = 1;
      while (lo <= hi) {
        var mid = (lo + hi) >> 1;
        if (fits(units.slice(start, start + mid))) { best = mid; lo = mid + 1; }
        else { hi = mid - 1; }
      }
      var end = start + best;
      if (end < units.length && !prose) {   // prefer to break where the poet did
        for (var b = end - 1; b > start + best / 2; b--) {
          if (!String(units[b]).trim()) { end = b; break; }
        }
      }
      chunks.push(units.slice(start, end));
      start = end;
      while (start < units.length && !String(units[start]).trim()) start++;
    }

    // A part must never be just the closing *** rule or blank lines. When the
    // last chunk has no actual words, fold it back into the one before it; if
    // that will not fit, hand the last chunk a real line so it is never a page
    // of ornament on its own.
    function meaty(arr) {
      return /[^\s\u2733*.\u00b7\u2014\u2013-]/.test(
        arr.join("\n").replace(/<[^>]*>/g, ""));
    }
    while (chunks.length > 1 && !meaty(chunks[chunks.length - 1])) {
      var tail = chunks.pop();
      var prev = chunks.pop();
      if (fits(prev.concat(tail))) {
        chunks.push(prev.concat(tail));
      } else {
        // keep pulling lines down until the last part actually has words —
        // pulling exactly one can hand it a blank line and change nothing
        while (prev.length > 1 && !meaty(tail)) tail.unshift(prev.pop());
        chunks.push(prev);
        chunks.push(tail);
        break;
      }
    }

    var num = page.querySelector(".page-num");
    var folio = num ? num.textContent : "";
    return chunks.map(function (c, i) {
      body.innerHTML = c.join(glue);
      if (num) num.textContent = folio + " · भाग " + (i + 1) + "/" + chunks.length;
      return page.outerHTML;
    });
  }

  /* A block can be taller than a short leaf on its own — a section's whole
     list, or the epigraph. Re-cut such a block into several copies of itself,
     each carrying as much as there is room for. */
  function expandBlocks(page, holder, blocks) {
    var out = [];
    function fitsNow() { return page.scrollHeight <= page.clientHeight + 1; }
    blocks.forEach(function (b) {
      holder.innerHTML = "";
      holder.appendChild(b);
      if (fitsNow()) { out.push(b); return; }

      var ul = b.querySelector && b.querySelector("ul");
      var units, apply;
      if (ul && ul.children.length > 1) {
        units = Array.prototype.map.call(ul.children, function (li) { return li.outerHTML; });
        apply = function (c, arr) { c.querySelector("ul").innerHTML = arr.join(""); };
      } else if (b.innerHTML && b.innerHTML.indexOf("\n") > -1) {
        units = b.innerHTML.split("\n");
        apply = function (c, arr) { c.innerHTML = arr.join("\n"); };
      } else { out.push(b); return; }

      var made = [], cur = [];
      for (var k = 0; k < units.length; k++) {
        cur.push(units[k]);
        var probe = b.cloneNode(true); apply(probe, cur);
        holder.innerHTML = ""; holder.appendChild(probe);
        if (cur.length > 1 && !fitsNow()) {
          cur.pop();
          var done = b.cloneNode(true); apply(done, cur);
          made.push(done);
          cur = [units[k]];
        }
      }
      if (cur.length) { var last = b.cloneNode(true); apply(last, cur); made.push(last); }
      made.forEach(function (m) { out.push(m); });
    });
    return out;
  }

  /* deal a page's block children out over as many leaves as they need */
  function splitBlocks(page, cols) {
    var blocks = [];
    Array.prototype.slice.call(page.children).forEach(function (n) {
      if (n === cols) Array.prototype.forEach.call(cols.children, function (c) { blocks.push(c); });
      else blocks.push(n);
    });
    blocks.forEach(function (b) { if (b.parentNode) b.parentNode.removeChild(b); });
    while (page.firstChild) page.removeChild(page.firstChild);
    var holder = document.createElement("div");
    holder.className = "toc-cols";
    page.appendChild(holder);

    blocks = expandBlocks(page, holder, blocks);
    holder.innerHTML = "";

    var groups = [], grp = [];
    for (var q = 0; q < blocks.length; q++) {
      holder.appendChild(blocks[q]);
      grp.push(blocks[q]);
      if (grp.length > 1 && page.scrollHeight > page.clientHeight + 1) {
        holder.removeChild(blocks[q]);
        grp.pop();
        groups.push(grp);
        holder.innerHTML = "";
        grp = [blocks[q]];
        holder.appendChild(blocks[q]);
      }
    }
    if (grp.length) groups.push(grp);
    return groups.map(function (g) {
      holder.innerHTML = "";
      g.forEach(function (b) { holder.appendChild(b); });
      return page.outerHTML;
    });
  }

  function partsFor(i) {
    if (i < 0 || i >= PAGES.length) return [""];
    var key = partsCacheKey();
    if (partsKey !== key) { PARTS.clear(); partsKey = key; }
    if (!PARTS.has(i)) {
      var html = CACHE.get(i);
      if (!html) return [""];                     // not cached yet; single part
      PARTS.set(i, isSingle() ? buildParts(html) : [html]);
    }
    return PARTS.get(i);
  }

  function partCount(i) {
    var p = partsFor(i);
    return p && p[0] ? p.length : 1;
  }

  var CACHE = new Map();          // page index -> fragment html, kept for the session

  function paint(el, i, p) {
    if (i < 0 || i >= PAGES.length) {
      el.innerHTML = '<div class="page plain"></div>';
      return Promise.resolve();
    }
    // A page already seen is re-hung straight from memory: no request, no
    // htmx round trip, nothing to parse twice.
    if (CACHE.has(i)) {
      var ps = partsFor(i);
      el.innerHTML = ps[Math.min(p || 0, ps.length - 1)] || CACHE.get(i);
      fitPage(el);
      return Promise.resolve();
    }
    warmed.add(i);
    return htmx.ajax("GET", fragUrl(i), { target: el, swap: "innerHTML" })
      .then(function () {
        CACHE.set(i, el.innerHTML);
        var q = partsFor(i);
        if (q.length > 1) el.innerHTML = q[Math.min(p || 0, q.length - 1)];
        fitPage(el);
      });
  }

  /* A printed page never scrolls, so shrink the type just enough that the
     longest poems still sit inside the leaf. */
  function fitPage(host) {
    var el = host.querySelector(".verse, .prose");
    if (!el) return;
    el.style.fontSize = "";
    el.style.lineHeight = "";
    if (el.scrollHeight <= el.clientHeight + 1) return;   // most pages fit as set

    // Scale relative to whatever the stylesheet set, so verse and prose each
    // shrink from their own starting point. Stepping down in fixed increments
    // meant up to 40 style-write/measure pairs and every one of those forces a
    // synchronous layout; the fit is monotonic, so binary search needs ~6.
    var cs = getComputedStyle(el);
    var base = parseFloat(cs.fontSize);
    var baseLh = parseFloat(cs.lineHeight) / base || 1.9;
    function apply(k) {
      el.style.fontSize = (base * k).toFixed(2) + "px";
      el.style.lineHeight = Math.max(1.3, baseLh - (1 - k) * 1.9).toFixed(2);
      return el.scrollHeight <= el.clientHeight + 1;
    }
    var lo = 0.46, hi = 1, best = lo;   // floor low enough that no page is ever cut
    if (!apply(lo)) return;                               // even the floor overflows
    for (var i = 0; i < 7; i++) {
      var mid = (lo + hi) / 2;
      if (apply(mid)) { best = mid; lo = mid; } else { hi = mid; }
    }
    apply(best);
  }

  /* The page is a fixed 460x640; rather than reflow it for short windows —
     which would re-break every poem — the whole book is scaled to whatever
     room the chrome leaves. Nothing is ever clipped, and the typography is
     identical at every size. */
  function fitBook() {
    var wrap = document.querySelector(".book-wrap");
    var stage = $("#bookStage");
    if (!wrap || !stage || !book) return;
    // Only the book's WIDTH is transitioned, so measuring it mid-turn returns a
    // half-animated number and the leaf visibly swells. Take the width from a
    // half (never animated) and derive the book's target from that; the height
    // is not animated, so the book itself is safe to measure.
    // getComputedStyle cannot be used for --leaf-w/--leaf-h: custom properties
    // come back as their unresolved token stream, e.g. "min(calc(100vh - …))".
    var half = book.querySelector(".half");
    var lw = half ? half.offsetWidth : 460;
    var h = book.offsetHeight;
    var oneLeaf = isSingle() || book.classList.contains("closed");
    var w = oneLeaf ? lw : lw * 2;
    if (!w || !h) return;
    var k = Math.max(0.3, Math.min(1, (wrap.clientHeight - 12) / h, (wrap.clientWidth - 12) / w));
    stage.style.transform = "scale(" + k.toFixed(4) + ")";
    stage.style.width = Math.round(w * k) + "px";
    stage.style.height = Math.round(h * k) + "px";
  }

  /* Re-fit every surface currently on screen. Needed because the first fit can
     run before the Devanagari webfont has arrived: the fallback face measures
     shorter, fitPage concludes the poem fits, and then the real font swaps in
     and overflows the leaf. */
  function fitAll() {
    document.querySelectorAll("#book .page").forEach(function (p) {
      fitPage(p);
    });
  }

  /* Warm the browser cache for nearby leaves so a turn never shows a gap. */
  /* The whole book is only a few hundred KB of fragments, so once the reader is
     open we quietly pull all of them into the cache while the browser is idle.
     After that every turn, jump and slider drag is instant and offline. */
  function warmAll() {
    var idle = window.requestIdleCallback || function (f) { return setTimeout(function () { f(null); }, 300); };
    var next = 0;
    (function pump() {
      var batch = 0;
      while (next < PAGES.length && batch < 6) {
        var i = next++;
        if (CACHE.has(i)) continue;
        batch++;
        (function (n) {
          fetch(fragUrl(n))
            .then(function (r) { return r.text(); })
            .then(function (t) { if (!CACHE.has(n)) CACHE.set(n, t); })
            .catch(function () {});
        })(i);
      }
      if (next < PAGES.length) idle(pump);
    })();
  }

  function prefetch(center) {
    for (var d = -3; d <= 4; d++) {
      var i = center + d;
      if (i < 0 || i >= PAGES.length || warmed.has(i)) continue;
      warmed.add(i);
      fetch(fragUrl(i));
    }
  }

  function isSingle() { return window.matchMedia("(max-width: 900px)").matches; }

  function render() {
    mode = isSingle() ? "single" : "spread";
    // The covers sit on their own, like a closed book, rather than opposite a blank leaf.
    book.classList.toggle("closed", idx === 0 || idx === PAGES.length - 1);
    var jobs = [paint(rightHalf, idx, part)];
    if (mode === "spread") jobs.push(paint(leftHalf, idx - 1));
    prefetch(idx);
    return Promise.all(jobs).then(syncChrome).then(fitBook);
  }

  /* ---------- the turn -------------------------------------------------- */
  function step() { return mode === "spread" ? 2 : 1; }

  function canNext() {
    return part + 1 < partCount(idx) || idx + step() < PAGES.length;
  }
  function canPrev() { return part > 0 || idx - step() >= 0; }

  /* In a spread the blank leaf is meaningful — it faces the title page, as it
     does in the printed book. Alone on a phone it is just a screen of nothing,
     so navigation steps over it. */
  function skippable(i) {
    return isSingle() && PAGES[i] && PAGES[i].kind === "blank";
  }

  /* the next / previous (page, part) pair */
  function nextCursor(dir) {
    if (dir > 0) {
      if (part + 1 < partCount(idx)) return { i: idx, p: part + 1 };
      var f = idx + step();
      while (skippable(f) && f + step() < PAGES.length) f += step();
      return { i: f, p: 0 };
    }
    if (part > 0) return { i: idx, p: part - 1 };
    var i = idx - step();
    while (skippable(i) && i - step() >= 0) i -= step();
    return { i: i, p: Math.max(0, partCount(i) - 1) };
  }

  function turn(dir) {
    if (busy) return Promise.resolve();
    if (dir > 0 ? !canNext() : !canPrev()) return Promise.resolve();
    busy = true;

    var s = step();
    var to = nextCursor(dir);                    // the (page, part) we are going to
    // Pages that ride on the two faces of the turning leaf.
    var frontIdx = dir > 0 ? idx : to.i;
    var frontPart = dir > 0 ? part : to.p;
    var backIdx = dir > 0 ? to.i : idx;
    var backPart = dir > 0 ? to.p : part;
    // What ends up underneath once the leaf has moved.
    var newIdx = to.i, newPart = to.p;
    var underRight = dir > 0 ? newIdx : idx;
    var underLeft = dir > 0 ? idx + 1 : newIdx - 1;

    var pre = [paint(leafFront, frontIdx, frontPart)];
    if (mode === "spread") pre.push(paint(leafBack, backIdx, backPart));

    return Promise.all(pre).then(function () {
      // Reveal what is beneath before the leaf starts moving.
      var under = [];
      if (dir > 0) {
        under.push(paint(rightHalf, underRight, dir > 0 ? newPart : part));
      } else if (mode === "spread") {
        under.push(paint(leftHalf, underLeft));
      }
      return Promise.all(under);
    }).then(function () {
      leaf.style.transition = "none";
      leaf.style.transform = dir > 0 ? "rotateY(0deg)" : "rotateY(-180deg)";
      leaf.classList.add("active");
      void leaf.offsetWidth;                       // commit the start state
      // Re-fit now that the faces certainly have a box. Synchronous, so the
      // browser never paints the unfitted state.
      fitPage(leafFront);
      fitPage(leafBack);
      leaf.style.transition = "";
      leaf.classList.add("turning");
      leaf.style.transform = dir > 0 ? "rotateY(-180deg)" : "rotateY(0deg)";

      return new Promise(function (done) {
        var finish = function () {
          leaf.removeEventListener("transitionend", finish);
          clearTimeout(t);
          done();
        };
        var t = setTimeout(finish, 1100);          // safety net
        leaf.addEventListener("transitionend", finish);
      });
    }).then(function () {
      idx = newIdx; part = newPart;
      var after = [];
      if (mode === "spread") {
        after.push(paint(leftHalf, idx - 1));
        if (dir < 0) after.push(paint(rightHalf, idx));
      } else {
        after.push(paint(rightHalf, idx, part));
      }
      return Promise.all(after);
    }).then(function () {
      leaf.classList.remove("active", "turning");
      leaf.style.transition = "none";
      leaf.style.transform = "rotateY(0deg)";
      void leaf.offsetWidth;
      leaf.style.transition = "";
      book.classList.toggle("closed", idx === 0 || idx === PAGES.length - 1);
      busy = false;
      prefetch(idx);
      syncChrome();
    });
  }

  /* ---------- jumping --------------------------------------------------- */
  function jumpTo(target) {
    if (busy) return;
    part = 0;
    target = Math.max(0, Math.min(PAGES.length - 1, target));
    // spreads are (idx-1, idx) with idx even, so an odd target sits on the left
    if (mode === "spread") target = target + (target % 2);
    if (target === idx) return;
    var dir = target > idx ? 1 : -1;
    var far = Math.abs(target - idx) > step() * 2;
    if (!far) {                                              // near: animate the turns
      turn(dir).then(function () { if (idx !== target) jumpTo(target); });
      return;
    }
    // far: riffle - fade the book, land, fade back in
    book.style.transition = "opacity .28s, transform .28s";
    book.style.opacity = "0";
    book.style.transform = "scale(.97) rotateY(" + (dir * 6) + "deg)";
    setTimeout(function () {
      idx = target;
      render().then(function () {
        book.style.opacity = "1";
        book.style.transform = "";
        setTimeout(function () { book.style.transition = ""; }, 300);
      });
    }, 280);
  }

  /* ---------- chrome ---------------------------------------------------- */
  function syncChrome() {
    var p = PAGES[idx] || {};
    var left = PAGES[idx - 1];
    var label;
    if (mode === "spread" && left && left.printed && p.printed) {
      label = "पन्ने " + left.printed + "–" + p.printed;
    } else if (p.printed) {
      label = "पन्ना " + p.printed;
      var n = partCount(idx);
      if (n > 1) label += " · भाग " + (part + 1) + "/" + n;
    } else {
      // only an actual cover is "कवर" — a continuation page has no heading and
      // was falling through to it
      label = p.heading || p.title || (p.kind === "cover" ? "कवर" : "उन्मुक्त मन");
      var m = partCount(idx);
      if (m > 1) label += " · भाग " + (part + 1) + "/" + m;
    }
    $("#pageLabel").textContent = label;
    $("#sectionLabel").textContent = p.section || "उन्मुक्त मन";
    syncRail(p.section || (left && left.section));

    // keep the address bar pointing at what is on screen, so pages are shareable
    var hash = p.printed ? "#p" + p.printed : "#read";
    if (location.hash !== hash) history.replaceState(null, "", hash);

    var slider = $("#slider");
    slider.max = PAGES.length - 1;
    slider.value = idx;

    $("#btnPrev").disabled = !canPrev();
    $("#btnNext").disabled = !canNext();

    document.querySelectorAll(".toc-list a").forEach(function (a) {
      a.classList.toggle("current", +a.dataset.index === idx ||
        (mode === "spread" && +a.dataset.index === idx + 1));
    });
  }

  /* ---------- the खंड rail ----------------------------------------------
     The contents drawer can already jump to a section, but that means opening
     a drawer first. This keeps all five within one tap of the page. */
  function buildRail() {
    var rail = $("#khandRail");
    if (!rail) return;
    rail.innerHTML = TOC.map(function (sec) {
      return '<button data-index="' + sec.start + '" data-section="' + sec.title + '"' +
             ' style="--tint:' + sec.tint + ';--accent:' + sec.accent + '">' +
             sec.title + '</button>';
    }).join("");
    rail.addEventListener("click", function (e) {
      var b = e.target.closest("[data-index]");
      if (b) jumpTo(+b.dataset.index);
    });
  }

  function syncRail(section) {
    var rail = $("#khandRail");
    if (!rail) return;
    rail.querySelectorAll("button").forEach(function (b) {
      b.classList.toggle("current", b.dataset.section === section);
    });
  }

  /* ---------- table of contents ----------------------------------------- */
  function buildToc() {
    var host = $("#tocBody");
    host.innerHTML = TOC.map(function (sec) {
      var items = sec.items.map(function (it) {
        var subs = (it.subs || []).map(function (s) {
          return '<li class="sub"><a href="#" data-index="' + s.index + '">' +
                 '<span>' + s.title + '</span></a></li>';
        }).join("");
        return '<li><a href="#" data-index="' + it.index + '">' +
               '<span>' + it.title + '</span>' +
               '<span class="pg">' + (it.printed || "") + '</span></a></li>' + subs;
      }).join("");
      return '<div class="toc-section" style="--tint:' + sec.tint + '">' +
             '<button data-index="' + sec.start + '">' +
             '<span>' + sec.title + '</span>' +
             '<span class="n">' + sec.items.length + '</span></button>' +
             '<ul class="toc-list">' + items + '</ul></div>';
    }).join("");

    host.addEventListener("click", function (e) {
      var t = e.target.closest("[data-index]");
      if (!t) return;
      e.preventDefault();
      closeToc();
      setTimeout(function () { jumpTo(+t.dataset.index); }, 260);
    });
  }

  function openToc() { $("#toc").classList.add("open"); $("#scrim").classList.add("on"); }
  function closeToc() { $("#toc").classList.remove("open"); $("#scrim").classList.remove("on"); }

  /* ---------- reader open/close ----------------------------------------- */
  function openReader(at) {
    $("#reader").classList.add("open");
    // the reader covers the page completely; animating what it hides is waste
    document.body.classList.add("reading");
    document.body.style.overflow = "hidden";
    idx = at || 0;
    part = 0;
    render();
    warmAll();
  }
  function closeReader() {
    $("#reader").classList.remove("open");
    document.body.classList.remove("reading");
    document.body.style.overflow = "";
    closeToc();
  }

  /* ---------- wiring ---------------------------------------------------- */
  function init() {
    book = $("#book");
    leftHalf = $("#halfLeft");
    rightHalf = $("#halfRight");
    leaf = $("#leaf");
    leafFront = $("#leafFront");
    leafBack = $("#leafBack");

    $("#btnNext").addEventListener("click", function () { turn(1); });
    $("#btnPrev").addEventListener("click", function () { turn(-1); });
    $("#btnToc").addEventListener("click", openToc);
    $("#tocClose").addEventListener("click", closeToc);
    $("#scrim").addEventListener("click", closeToc);
    $("#btnClose").addEventListener("click", closeReader);
    // every route into the book: the banner CTA, and the cover and button
    // on the featured volume
    ["#btnRead", "#volUnmukt", "#volCover"].forEach(function (sel) {
      var el = $(sel);
      if (el) el.addEventListener("click", function () { openReader(0); });
    });

    $("#slider").addEventListener("input", function () {
      var v = +this.value;
      $("#pageLabel").textContent = PAGES[v] && PAGES[v].printed
        ? "पन्ना " + PAGES[v].printed : (PAGES[v] ? PAGES[v].heading || "कवर" : "");
    });
    $("#slider").addEventListener("change", function () { jumpTo(+this.value); });

    document.addEventListener("keydown", function (e) {
      if (!$("#reader").classList.contains("open")) return;
      if (e.key === "ArrowRight" || e.key === "PageDown" || e.key === " ") { e.preventDefault(); turn(1); }
      if (e.key === "ArrowLeft" || e.key === "PageUp") { e.preventDefault(); turn(-1); }
      if (e.key === "Escape") { $("#toc").classList.contains("open") ? closeToc() : closeReader(); }
      if (e.key === "t" || e.key === "T") { $("#toc").classList.contains("open") ? closeToc() : openToc(); }
    });

    // click the outer third of a page to turn it, like a real book
    $(".book-wrap").addEventListener("click", function (e) {
      if (e.target.closest("a, button, .verse")) return;
      var r = book.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width;
      if (x > 0.62) turn(1); else if (x < 0.38) turn(-1);
    });

    // swipe on touch devices
    var sx = null, sy = null;
    $(".book-wrap").addEventListener("touchstart", function (e) {
      sx = e.touches[0].clientX;
      sy = e.touches[0].clientY;
    }, { passive: true });
    $(".book-wrap").addEventListener("touchend", function (e) {
      if (sx === null) return;
      var dx = e.changedTouches[0].clientX - sx;
      var dy = e.changedTouches[0].clientY - sy;
      // must be a decidedly sideways gesture: measuring dx alone let a mostly
      // vertical swipe with a little drift turn the page by accident
      if (Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy) * 1.4) turn(dx < 0 ? 1 : -1);
      sx = sy = null;
    }, { passive: true });

    var lastMode = isSingle();
    window.addEventListener("resize", function () {
      if (isSingle() !== lastMode) { lastMode = isSingle(); render(); }
    });

    buildToc();
    buildRail();

    // the real fit, once the verse face is actually available to measure
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () {
      fitAll(); fitBook();
    });
    window.addEventListener("resize", function () { fitAll(); fitBook(); });

    // #read opens at the cover, #p48 opens at printed page 48
    var m = /^#p(\d+)$/.exec(location.hash);
    if (m) {
      var want = PAGES.findIndex(function (p) { return p.printed === +m[1]; });
      if (want >= 0) openReader(isSingle() ? want : want + (want % 2));
    } else if (location.hash === "#read") {
      openReader(0);
    } else if (location.hash === "#contents") {
      openReader(0);
      setTimeout(openToc, 400);
    }
  }

  // always revalidate: this carries VERSION, so a stale copy here would
  // keep every fragment stale too
  fetch("data/book.json", { cache: "no-cache" })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      PAGES = d.pages; TOC = d.toc; VERSION = d.version || "";
      document.querySelectorAll("[data-count-poems]").forEach(function (el) { el.textContent = d.poemCount; });
      document.querySelectorAll("[data-count-pages]").forEach(function (el) { el.textContent = d.printedCount; });
      init();
    });
})();
