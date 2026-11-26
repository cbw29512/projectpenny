import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { MUGS, SHIRTS } from "../../website/assets/scene/office-collection.mjs";
const read=path=>readFileSync(new URL("../../"+path,import.meta.url),"utf8");
const escape=s=>s.replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
test("all fourteen shirts preserve exact original character geometry",()=>{
  const original=read("website/assets/scene/penny-v1.svg");
  for(const s of SHIRTS){
    const svg=read("website/assets/scene/shirts/"+s.id+".svg");
    const baseline=svg.replace(/  <g id="daily-shirt-print">[\s\S]*?<\/g>\n/,"")
      .replace(/(M187 180[^"]*" fill=")#[a-f0-9]{6}"/,'$1#429285"');
    assert.equal(baseline,original,s.id);
    for(const line of s.lines)assert.ok(svg.includes(escape(line)),s.id);
    assert.doesNotMatch(svg,/<script|<foreignObject|href=/i);
  }
});
test("six mug assets match literal designs and wardrobe override remains separate",()=>{
  for(const m of MUGS){
    const svg=read("website/assets/scene/mugs/"+m.id+".svg");
    for(const line of m.lines)assert.ok(svg.includes(escape(line)),m.id);
    assert.doesNotMatch(svg,/<script|<foreignObject|href=/i);
  }
  const html=read("website/index.html"),css=read("website/assets/scene/daily-style.css");
  assert.match(html,/id="daily-shirt-art" hidden/);
  assert.match(html,/id="daily-mug-art" hidden/);
  assert.ok(html.indexOf('id="daily-shirt-art"')<html.indexOf('src="/assets/scene/desk-v1.svg"'));
  assert.ok(css.includes('[data-world-layer="plum-outfit-v1"]:not([hidden]) ~ #daily-shirt-art'));
});
