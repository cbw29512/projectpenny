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

test("finance accepts signed integer cents and rejects malformed amounts",()=>{
  const finance={status:"recorded_unreconciled",net_receipts:900,expenses:250,recorded_cash:-50,community_support:300};
  assert.equal(validSnapshot({...s,finance},100),true);
  assert.equal(validSnapshot({...s,finance:null},100),true);
  assert.equal(validSnapshot({...s,finance:{...finance,recorded_cash:"0"}},100),false);
  assert.equal(validSnapshot({...s,finance:{...finance,status:"verified"}},100),false);
});
