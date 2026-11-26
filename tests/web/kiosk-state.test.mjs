import test from "node:test";
import assert from "node:assert/strict";
import { validSnapshot } from "../../kiosk/state.mjs";
const s = {sampled_at:100,paused:false,enabled:true,uncertain:false,visitor_busy:false,
  counts:{queued:1},recent:[],active:null,latest_plan:null,latest_measurement:null};
test("live kiosk requires fresh, structurally valid evidence",()=>{
  assert.equal(validSnapshot(s,110),true);
  assert.equal(validSnapshot(s,111),false);
  assert.equal(validSnapshot(s,97),false);
  for(const patch of [{counts:null},{enabled:"true"},{recent:[null]},
    {active:{started_at:101,lease_until:120}},{latest_measurement:{target:0}},
    {latest_plan:undefined},{counts:{queued:-1}}])
    assert.equal(validSnapshot({...s,...patch},100),false);
});
test("expired lease remains valid evidence of interruption",()=>{
  assert.equal(validSnapshot({...s,active:{started_at:80,lease_until:90}},100),true);
});
