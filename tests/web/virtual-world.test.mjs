import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { LAYERS, parseWorld, acceptWorld } from "../../website/assets/scene/world-state.mjs";
import { worldRenderer } from "../../website/assets/scene/world-render.mjs";

const sample = {schema:"penny-world-v1", status:"reviewed_virtual_preview",
  baseline:"preview-v1", revision:4, placements:{"plant-v1":"left-shelf"},
  outfit:"plum-outfit-v1"};
const parse = value => parseWorld(JSON.stringify(value));
const read = path => readFileSync(new URL("../../" + path, import.meta.url), "utf8");

test("rejects unknown asset, slot, outfit, collision, identity and extra fields", () => {
  for (const changes of [
    {placements:{"evil.svg":"left-shelf"}}, {placements:{"plant-v1":"url(x)"}},
    {placements:{"plant-v1":"left-shelf","mug-v1":"left-shelf"}},
    {outfit:"new-face"}, {baseline:"new-office"}, {html:"<script>"},
    {revision:1}, {revision:2049}, {placements:null}, {status:"unavailable"}
  ]) assert.equal(parse({...sample,...changes}), null);
  assert.equal(parseWorld("{"), null);
  assert.equal(parseWorld("x".repeat(2049)), null);
});

test("invalid or regressed or conflicting revision preserves current scene", () => {
  const current = parse(sample);
  assert.ok(current);
  for (const candidate of [null, parse({...sample,revision:3,outfit:null}),
      parse({...sample,placements:{"plant-v1":"right-shelf"}})]) {
    assert.deepEqual(acceptWorld(current,candidate), {state:current,accepted:false});
  }
  assert.equal(acceptWorld(current,parse({...sample,revision:5})).accepted,true);
});

test("only pre-existing layers change; remove and move preserve other assets", () => {
  const base = {hidden:false}, notice = {};
  const nodes = new Map(LAYERS.map(id => ['[data-world-layer="' + id + '"]',{hidden:true}]));
  nodes.set("[data-world-base]",base);
  const render = worldRenderer({querySelector:key=>nodes.get(key)},notice);
  assert.equal(render(JSON.stringify(sample)),true);
  assert.equal(base.hidden,true);
  assert.equal(nodes.get('[data-world-layer="plant-v1:left-shelf"]').hidden,false);
  assert.equal(render("{"),false);
  assert.equal(base.hidden,true);
  assert.match(notice.textContent,/Last reviewed/);
  const moved = {...sample,revision:5,placements:{"plant-v1":"right-shelf"}};
  assert.equal(render(JSON.stringify(moved)),true);
  assert.equal(nodes.get('[data-world-layer="plant-v1:left-shelf"]').hidden,true);
  assert.equal(nodes.get('[data-world-layer="plant-v1:right-shelf"]').hidden,false);
  assert.equal(base.hidden,true);
  assert.equal(render(JSON.stringify({...moved,revision:6,outfit:null})),true);
  assert.equal(base.hidden,false);
  assert.equal(nodes.get('[data-world-layer="plant-v1:right-shelf"]').hidden,false);
});

test("alternate character changes shirt color only; all overlay nodes are static", () => {
  const original = read("website/assets/scene/penny-v1.svg");
  const alternate = read("website/assets/scene/plum-outfit-v1.svg");
  assert.equal(alternate,original.replace('fill="#429285"','fill="#805477"'));
  const html = read("website/index.html");
  assert.deepEqual([...html.matchAll(/data-world-layer="([^"]+)"/g)].map(m=>m[1]).sort(),
    [...LAYERS].sort());
  assert.equal([...html.matchAll(/data-world-layer="[^"]+" hidden/g)].length,LAYERS.length);
  assert.match(html,/id="world-snapshot">\{"schema":"penny-world-v1","status":"unavailable"\}/);
});
