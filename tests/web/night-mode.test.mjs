import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { PAJAMAS,pajamasFor } from "../../website/assets/scene/office-pajamas.mjs";
import { parseRest,nightView } from "../../website/assets/scene/night-state.mjs";
import { nightPresenter } from "../../website/assets/scene/night-render.mjs";
import { updateBit } from "../../website/assets/scene/bit-render.mjs";
const epoch=s=>Date.parse(s)/1000;
const now=epoch("2026-11-27T05:00:00Z"),wake=epoch("2026-11-27T13:00:00Z");
const rest={schema:"penny-rest-v1",status:"reviewed",policy:"rest-concept-v1",state:"asleep",sampled_at:now,expires_at:now+60,wake_at:wake,gate_closed:true,active:false};
const text=(v={})=>JSON.stringify({...rest,...v});
test("seven civil-date variants and exact identity",()=>{
  const read=p=>readFileSync(new URL("../../"+p,import.meta.url),"utf8");
  const base=read("website/assets/scene/penny-v1.svg");
  assert.equal(PAJAMAS.length,7);
  assert.equal(new Set(Array.from({length:7},(_,i)=>pajamasFor("2026-11-"+(23+i)).id)).size,7);
  assert.equal(pajamasFor("2026-11-23").id,pajamasFor("2026-11-30").id);
  assert.equal(pajamasFor("2026-02-30"),null);
  for(const p of PAJAMAS){
    const svg=read("website/assets/scene/pajamas/"+p.id+".svg");
    assert.equal(svg.replace(/  <g id="pajama-print">[\s\S]*?<\/g>\n/,"").replace(/(M187 180[^"]*" fill=")#[a-f0-9]{6}"/,'$1#429285"'),base);
  }
});
test("sleep requires fresh reviewed closed gate and no active task",()=>{
  const s=parseRest(text(),now);assert.equal(nightView(s,now).minutes,480);
  for(const v of [{active:true},{gate_closed:false},{wake_at:wake+3600},{status:"unavailable"},{extra:true}])
    assert.equal(parseRest(text(v),now),null);
  assert.equal(parseRest(text(),now+60),null);
  assert.equal(parseRest(text({sampled_at:wake,expires_at:wake+60}),wake),null);
  assert.equal(parseRest(text({state:"draining",wake_at:null,active:true}),now).state,"draining");
});
test("demo never claims sleep, reviewed state supersedes demo, stale state clears sleep",()=>{
  const scene={dataset:{}},art={hidden:true},notice={},link={};
  const view=nightPresenter(scene,art,notice,link);
  assert.equal(view.preview("2026-11-27"),true);
  assert.equal(scene.dataset.nightMode,"preview");assert.match(notice.textContent,/preview only/);
  assert.equal(view.review(text(),now),true);assert.equal(scene.dataset.nightMode,"reviewed");
  assert.equal(view.preview("2026-11-28"),false);
  assert.equal(view.review(text(),now+60),false);assert.equal(art.hidden,true);
  assert.equal(scene.dataset.nightMode,undefined);
  const bit={hidden:false,dataset:{}};
  assert.equal(updateBit(bit,"{}",now,text()),"charging");
  bit.hidden=true;assert.equal(updateBit(bit,"{}",now,text()),"idle");
});
