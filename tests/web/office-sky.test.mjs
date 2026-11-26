import test from "node:test";
import assert from "node:assert/strict";
import { skyAt, easternClock, OFFICE_SKY } from "../../website/assets/scene/office-sky.mjs";
const at=s=>skyAt(Date.parse(s));
test("fixed Eastern location, summer and winter daylight and nighttime",()=>{
  assert.equal(OFFICE_SKY.zone,"America/New_York");
  assert.equal(at("2026-06-21T17:00:00Z").period,"day");
  assert.equal(at("2026-12-21T17:00:00Z").period,"day");
  assert.ok(at("2026-06-21T17:00:00Z").sun.alt>at("2026-12-21T17:00:00Z").sun.alt+35);
  assert.equal(at("2026-12-21T05:00:00Z").period,"night");
  assert.equal(at("2026-12-21T05:00:00Z").sunVisible,false);
});
test("known new/full lunar dates and horizon gate",()=>{
  const eclipse=at("2024-04-08T18:21:00Z");
  assert.equal(eclipse.phase,"New moon");
  assert.ok(eclipse.illumination<0.02);
  const full=at("2024-03-25T07:00:00Z");
  assert.equal(full.phase,"Full moon");
  assert.ok(full.illumination>0.98);
  const cycle=Array.from({length:24},(_,i)=>skyAt(Date.UTC(2024,2,25,i)));
  assert.ok(cycle.some(s=>s.moonVisible));
  assert.ok(cycle.some(s=>s.moon.alt<0 && !s.moonVisible));
  for(const s of cycle)assert.ok(!s.moonVisible||s.moon.alt>1);
});
test("Eastern clock handles DST and midnight without visitor timezone",()=>{
  assert.match(easternClock(Date.parse("2026-03-08T06:59:00Z")),/1:59.*EST/);
  assert.match(easternClock(Date.parse("2026-03-08T07:00:00Z")),/3:00.*EDT/);
  assert.match(easternClock(Date.parse("2026-11-01T05:59:00Z")),/1:59.*EDT/);
  assert.match(easternClock(Date.parse("2026-11-01T06:00:00Z")),/1:00.*EST/);
  assert.match(easternClock(Date.parse("2026-11-26T04:59:00Z")),/Nov 25/);
  assert.equal(skyAt(NaN),null);
  assert.equal(skyAt(Date.UTC(2100,0,1)),null);
});
