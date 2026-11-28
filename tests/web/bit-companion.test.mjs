import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { parseWorld } from "../../website/assets/scene/world-state.mjs";
import { bitReaction } from "../../website/assets/scene/bit-state.mjs";
import { updateBit } from "../../website/assets/scene/bit-render.mjs";

const snapshot={schema:"penny-world-v1",status:"reviewed_virtual_preview",
  baseline:"preview-v1",revision:2,placements:{"bit-v1":"bit-dock"},outfit:null};
const activity=(code,event=null)=>JSON.stringify({schema:"penny-bit-activity-v1",
  status:"reviewed",activity:code,sampled_at:1000,event_at:event});

test("Bit is placed only in his dedicated slot in a valid world snapshot",()=>{
  assert.deepEqual(parseWorld(JSON.stringify(snapshot)).layers,["bit-v1:bit-dock"]);
  assert.equal(parseWorld(JSON.stringify({...snapshot,placements:{"bit-v1":"left-shelf"}})),null);
  assert.equal(parseWorld(JSON.stringify({...snapshot,placements:{"plant-v1":"bit-dock"}})),null);
  assert.equal(parseWorld(JSON.stringify({...snapshot,revision:1})),null);
});
test("coded reactions are fresh, finite, and default to idle",()=>{
  assert.equal(bitReaction(activity("working"),1000),"attentive");
  assert.equal(bitReaction(activity("answering"),1000),"attentive");
  assert.equal(bitReaction(activity("asleep"),1000),"charging");
  assert.equal(bitReaction(activity("verified_sale",995),1000),"celebrating");
  assert.equal(bitReaction(activity("verified_sale",980),1000),"idle");
  assert.equal(bitReaction(activity("error",995),1000),"confused");
  assert.equal(bitReaction(activity("working"),1060),"idle");
  assert.equal(bitReaction(activity("https://evil"),1000),"idle");
  assert.equal(bitReaction(activity("verified_achievement",1001),1000),"idle");
  const node={hidden:true,dataset:{}};
  assert.equal(updateBit(node,activity("verified_sale",995),1000),"idle");
  assert.equal(node.hidden,true);
  node.hidden=false;
  assert.equal(updateBit(node,activity("verified_sale",995),1000),"celebrating");
  assert.equal(node.src,"/assets/scene/bit/bit-celebrating-v1.svg");
});
test("all expressions preserve body artwork and no default ownership",()=>{
  const read=path=>readFileSync(new URL("../../"+path,import.meta.url),"utf8");
  const body=s=>s.split("\n").filter(l=>!l.includes('y="25"')&&!l.includes('y="22"')
    &&!l.includes("M27 31")&&!l.includes("M25 32")&&!l.includes("M37 42")
    &&!l.includes("M39 42")&&!l.includes("M36 40")).join("\n");
  const idle=read("website/assets/scene/bit/bit-idle-v1.svg");
  for(const mode of ["attentive","celebrating","confused","charging"])
    assert.equal(body(read("website/assets/scene/bit/bit-"+mode+"-v1.svg")),body(idle));
  assert.match(read("website/index.html"),/data-world-layer="bit-v1:bit-dock" hidden/);
});
