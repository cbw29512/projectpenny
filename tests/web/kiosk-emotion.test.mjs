import test from "node:test";
import assert from "node:assert/strict";
import {reaction, expressions} from "../../kiosk/emotion.mjs";
const base = {sampled_at:1000,active:null,visitor_busy:false,uncertain:false,paused:false,enabled:true,counts:{},recent:[],latest_measurement:null};
const draft = {status:"succeeded",finished_at:990,hypothesis:"unverified demand"};
test("idle and stale never celebrate",()=>{
  assert.equal(reaction(base).emotion,"neutral");
  assert.equal(reaction(null).emotion,"neutral");
  assert.equal(reaction({...base,recent:[{...draft,finished_at:1}]}).emotion,"neutral");
});
test("real active work and uncertainty take precedence",()=>{
  assert.equal(reaction({...base,active:{lease_until:1100},recent:[draft]}).emotion,"focused");
  assert.equal(reaction({...base,active:{lease_until:999}}).emotion,"concerned");
  assert.equal(reaction({...base,uncertain:true,recent:[draft]}).emotion,"concerned");
});
test("task completion is not business success",()=>{
  const r=reaction({...base,recent:[draft]});
  assert.equal(r.emotion,"pleased");
  assert.match(r.comment,/not yet/);
  assert.equal(reaction({...base,recent:[{...draft,hypothesis:null}]}).emotion,"reflective");
  assert.equal(reaction({...base,recent:[{...draft,status:"failed"}]}).emotion,"reflective");
});
test("measured outcome determines celebration or disappointment",()=>{
  const m={recorded_at:999,target:5,measured_count:3};
  const miss=reaction({...base,latest_measurement:m});
  assert.equal(miss.emotion,"disappointed");
  assert.match(miss.comment,/3 of 5/);
  assert.match(miss.comment,/cause is not yet established/);
  assert.equal(reaction({...base,latest_measurement:{...m,measured_count:5}}).emotion,"celebrating");
  assert.equal(reaction({...base,latest_measurement:{...m,measured_count:null}}).emotion,"neutral");
});
test("every reaction has a face; no pretend planning",()=>{
  assert.equal(reaction({...base,paused:true}).emotion,"patient");
  assert.equal(reaction({...base,latest_plan:{outcome:"no_eligible_work"}}).emotion,"patient");
  for(const r of [reaction(base),reaction(null),reaction({...base,paused:true})])
    assert.ok(expressions[r.emotion]);
});
