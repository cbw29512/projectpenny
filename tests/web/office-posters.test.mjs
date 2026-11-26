import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { POSTERS } from "../../website/assets/scene/office-posters.mjs";
import { MUGS, SHIRTS } from "../../website/assets/scene/office-collection.mjs";

test("thirty immutable poster concepts have independent versioned IDs and literal text", () => {
  assert.equal(POSTERS.length, 30);
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
  assert.equal(new Set(POSTERS.map(p=>p.phrase)).size,30);
  for(const p of POSTERS) {
    const svg=readFileSync(new URL("../../website/assets/scene/posters/"+p.id+".svg",import.meta.url),"utf8");
    assert.ok(svg.includes(p.title.replaceAll("&","&amp;")), p.id+" title");
    for(const line of p.lines) assert.ok(svg.includes(line.replaceAll("&","&amp;")));
    assert.doesNotMatch(svg,/<script|<foreignObject|href=/i);
  }
  const scene=html.split('id="penny-scene"')[1].split("</div>")[0];
  assert.equal((scene.match(/data-daily-poster-frame/g)||[]).length,1);
  assert.match(scene,/data-daily-poster-frame hidden/);
});
