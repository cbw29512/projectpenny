import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {timelineState,parseTimeline,filterEvents} from "../../website/assets/timeline-state.mjs";

const NOW=1700000000;
const DAY=Math.floor(NOW/86400)*86400;
function fixture(){
  return {schema:"penny-timeline-v1",status:"reviewed",generated_at:NOW-5,expires_at:NOW+60,
    events:["corrected","target_met","target_missed","experiment_stopped","experiment_rejected"]
      .map((kind,i)=>({kind,day_epoch:DAY-i*86400}))};
}
test("reviewed outcomes retain order and filter without hiding failures by default",()=>{
  const state=timelineState(fixture(),NOW);
  assert.equal(state.status,"reviewed");
  assert.equal(filterEvents(state,"all").length,5);
  assert.deepEqual(filterEvents(state,"victories").map(x=>x.kind),["target_met"]);
  assert.deepEqual(filterEvents(state,"setbacks").map(x=>x.kind),["target_missed"]);
  assert.equal(filterEvents(state,"discontinued").length,2);
  assert.equal(filterEvents(state,"corrections").length,1);
  assert.equal(filterEvents(state,"all")[0].date,"2023-11-14");
  assert.deepEqual(filterEvents(state,"__proto__"),[]);
});
test("expired and unavailable data expose no events",()=>{
  const state=timelineState(fixture(),NOW+60);
  assert.equal(state.status,"stale");
  assert.deepEqual(filterEvents(state,"all"),[]);
  assert.equal(timelineState({schema:"penny-timeline-v1",status:"unavailable",events:[]},NOW).status,"unavailable");
});
test("reject unknown kind, private fields, unordered and invalid dates or oversize",()=>{
  for(const change of [
    r=>r.events[0].kind="__proto__",
    r=>r.events[0].name="private",
    r=>r.events[0].day_epoch=DAY+86400,
    r=>r.events[0].day_epoch=DAY-1,
    r=>r.events.reverse(),
    r=>r.events=Array.from({length:21},()=>r.events[0]),
    r=>r.events=[],
    r=>r.generated_at=NOW+1,
    r=>r.expires_at=NOW+3601,
    r=>r.private="secret",
  ]){
    const raw=fixture();change(raw);
    assert.equal(timelineState(raw,NOW).status,"unavailable");
  }
  assert.equal(parseTimeline("{",NOW).status,"unavailable");
  assert.equal(parseTimeline(" ".repeat(8193),NOW).status,"unavailable");
});
test("static diary has no real or synthetic events and uses text-only rendering",()=>{
  const html=readFileSync("website/index.html","utf8");
  const source=html.match(/<script type="application\/json" id="timeline-snapshot">([^<]+)<\/script>/);
  assert.ok(source);
  assert.deepEqual(JSON.parse(source[1]),{schema:"penny-timeline-v1",status:"unavailable",events:[]});
  assert.match(html,/id="timeline-filter" disabled/);
  assert.match(html,/id="timeline-events"/);
  assert.doesNotMatch(readFileSync("website/assets/timeline.mjs","utf8"),/\bfetch\s*\(|innerHTML\s*=/);
  assert.match(readFileSync("website/_headers","utf8"),/connect-src 'none'/);
});
