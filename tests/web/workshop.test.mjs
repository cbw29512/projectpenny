import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {workshopState,parseWorkshop,stageLabel} from "../../website/assets/workshop-state.mjs";
const NOW=1700000000;
const fixture=()=>({schema:"penny-workshop-v1",status:"reviewed",product:"packing-checklist-v1",
  stage:"prototype_reviewed",generated_at:NOW-5,expires_at:NOW+60});
test("only exact reviewed known stage displays",()=>{
  const state=workshopState(fixture(),NOW);
  assert.equal(state.status,"reviewed");
  assert.match(stageLabel(state),/private prototype/);
  assert.equal(workshopState(fixture(),NOW+60).status,"stale");
  assert.equal(stageLabel(workshopState(fixture(),NOW+60)),"Development status unavailable.");
});
test("reject unknown product, private payloads, future timestamps and unsafe stage",()=>{
  for(const mutate of [
    r=>r.product="unknown",r=>r.stage="__proto__",r=>r.stage="<script>",
    r=>r.member_id="private",r=>r.content="private",r=>r.generated_at=NOW+1,
    r=>r.expires_at=NOW+3601,r=>r.status="released",
  ]){
    const r=fixture();mutate(r);
    assert.equal(workshopState(r,NOW).status,"unavailable");
  }
  assert.equal(parseWorkshop("{",NOW).status,"unavailable");
  assert.equal(parseWorkshop(" ".repeat(1025),NOW).status,"unavailable");
});
test("public development Workshop has no live data, network or enabled submission",()=>{
  const html=readFileSync("website/index.html","utf8");
  const source=html.match(/<script type="application\/json" id="workshop-snapshot">([^<]+)<\/script>/);
  assert.ok(source);
  assert.deepEqual(JSON.parse(source[1]),{schema:"penny-workshop-v1",status:"unavailable"});
  assert.match(html,/href="#workshop"/);
  assert.match(html,/id="workshop"/);
  assert.match(html,/<button type="button" disabled id="workshop-feedback"/);
  assert.match(html,/<button type="button" disabled id="workshop-beta"/);
  const renderer=readFileSync("website/assets/workshop.mjs","utf8");
  assert.doesNotMatch(renderer,/\bfetch\s*\(|innerHTML\s*=|localStorage|sessionStorage/);
  assert.match(readFileSync("website/_headers","utf8"),/connect-src 'none'/);
});
