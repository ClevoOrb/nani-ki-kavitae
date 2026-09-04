// Stamp a content hash onto every stylesheet and script referenced by
// index.html, so a changed file is a changed URL and a deploy takes effect on
// the next page load. Vercel runs this as the build step, so it is never
// something anyone has to remember.
//
// Node only, no dependencies.

import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, existsSync } from "node:fs";

const INDEX = "index.html";
const REF = /((?:href|src)=")((?:css|js)\/[^"?]+)(\?v=[^"]*)?(")/g;

const html = readFileSync(INDEX, "utf8");
const seen = new Map();
let missing = 0;

const out = html.replace(REF, (whole, prefix, rel, _old, close) => {
  if (!existsSync(rel)) {
    console.error(`  !! ${rel} is referenced by ${INDEX} but does not exist`);
    missing++;
    return whole;
  }
  if (!seen.has(rel)) {
    seen.set(rel, createHash("sha1").update(readFileSync(rel)).digest("hex").slice(0, 8));
  }
  return `${prefix}${rel}?v=${seen.get(rel)}${close}`;
});

if (missing) {
  console.error(`\n  ${missing} referenced file(s) missing — refusing to build.`);
  process.exit(1);
}

for (const [rel, h] of [...seen].sort()) console.log(`  ${rel.padEnd(22)} v=${h}`);

if (out !== html) {
  writeFileSync(INDEX, out);
  console.log(`  ${INDEX} restamped`);
} else {
  console.log(`  ${INDEX} already current`);
}
