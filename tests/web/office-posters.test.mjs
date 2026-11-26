import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { POSTERS } from "../../website/assets/scene/office-posters.mjs";
import { MUGS, SHIRTS } from "../../website/assets/scene/office-collection.mjs";

test("six immutable poster concepts have independent versioned IDs and literal text", () => {
  assert.equal(POSTERS.length, 6);
  assert.ok(Object.isFrozen(POSTERS));
  const ids = [...POSTERS,...MUGS,...SHIRTS].map(p=>p.id);
  assert.equal(new Set(ids).size, ids.length);
  for (const p of POSTERS) {
    assert.match(p.id,/^poster-[a-z-]+-v1$/);
    assert.equal(p.phrase,p.lines.join(" "));
    assert.ok(Object.isFrozen(p) && Object.isFrozen(p.lines));
  }
  assert.equal(POSTERS.find(p=>p.id==="poster-mission-v1").phrase,"$0 to $1,000,000");
});

test("all poster themes exist and the read-only catalog has a separate wall art section",()=>{
  const css=readFileSync(new URL("../../website/assets/scene/office-collection.css",import.meta.url),"utf8");
  const html=readFileSync(new URL("../../website/index.html",import.meta.url),"utf8");
  for(const p of POSTERS) assert.ok(css.includes(".poster-concept."+p.theme+" {"));
  assert.ok(html.includes('id="collection-posters"'));
  // No new scene geometry or implicit poster ownership in the canonical scene.
  const scene=html.split('id="penny-scene"')[1].split("</div>")[0];
  assert.ok(!scene.includes("poster-"));
});
