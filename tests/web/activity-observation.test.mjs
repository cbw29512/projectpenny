import test from "node:test";
import assert from "node:assert/strict";
import {observationView} from "../../website/assets/activity-observation.mjs";
test("cached observations are labeled historical and expire without renewing",()=>{
  const sample={sampled_at:1000,activity:"working"};
  assert.deepEqual(observationView(sample,1119),{label:"Last observed: Working",sampledAt:1000});
  assert.equal(observationView(sample,1120),null);
  assert.equal(observationView(sample,999),null);
  assert.equal(observationView({...sample,private:"hidden"},1000),null);
  assert.equal(observationView({...sample,activity:"<script>"},1000),null);
  assert.equal(observationView({...sample,activity:"off_duty"},1000).label,"Last observed: Off duty");
});
