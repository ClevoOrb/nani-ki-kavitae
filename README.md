# नानी की कविताएँ

The collected poetry of **रूक्मिणी बड़जातिया** (Rukmini Badjatia), and a reader for
her first published collection, *उन्मुक्त मन* (2006) — ninety pages, ninety-four poems
in five खंड.

Made as a birthday gift by Pranav Gangwal, 4 September 2026.

## The site

A static site. `index.html` at the repository root is the whole entry point; the reader
loads each page of the book as an htmx fragment from `fragments/`.

```
index.html      the banner, the shelf of collections, the poet, the dedication
css/            base.css (type + colour), hero.css (the banner), reader.css (the book)
js/             book.js (the reader), petals.js (the banner's drifting syllables),
                htmx.min.js (self-hosted)
assets/         the artwork, covers and the page ornaments
data/book.json  the page manifest, contents and a build stamp
fragments/      106 page fragments, one per leaf of the book
```

## The text

Every page was read by several vision models, reconciled line by line, and then
proof-read by hand against the scans — 543 corrections were made by hand and each was
checked a second time. `source/ocr/final.json` is the adjudicated text and
`source/ocr/overrides.json` the human corrections layered over it; together they are the
authority for every word on the site. `source/work/build_site.py` regenerates
`fragments/` and `data/book.json` from them.

## The reader

- Two-page spread on wide screens, a single leaf on phones.
- On a phone a long page is dealt out over several parts at one readable size, marked
  `पन्ना 30 · भाग 1/3`, rather than being shrunk to fit.
- Page turns by arrow, keyboard, swipe, or tapping the edge of a leaf.
- `_audit.html` and `_parts.html` (kept out of this repository) verify that no page ever
  loses a line at any screen size.

*परस्परोपग्रहो जीवानाम् ॥*
