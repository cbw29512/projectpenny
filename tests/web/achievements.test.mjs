import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {CODES,achievementState,parseAchievements,awardDisplay} from "../../website/assets/achievement-state.mjs";

const NOW=1700000000,DAY=Math.floor(NOW/86400)*86400;
const fixture=()=>({schema:"penny-achievements-v1",status:"reviewed",
  generated_at:NOW-5,expires_at:NOW+60,
  achievements:CODES.map((code,i)=>({code,status:i===0?"verified":i===1?"needs_review":"withdrawn",
    review_day:i===0?DAY:null}))});
test("verified award displays UTC review date and only current approval",()=>{
  const state=achievementState(fixture(),NOW);
  assert.equal(state.status,"reviewed");
  assert.deepEqual(awardDisplay(state,"first_dollar"),{label:"Verified",verified:true,date:"2023-11-14"});
  assert.deepEqual(awardDisplay(state,"in_the_green"),{label:"Needs review",verified:false,date:""});
  assert.deepEqual(awardDisplay(state,"proof_of_concept"),{label:"Withdrawn",verified:false,date:""});
  assert.equal(awardDisplay(state,"hello_world").verified,false);
});
test("expired and unavailable snapshots clear award verification",()=>{
  const state=achievementState(fixture(),NOW+60);
  assert.equal(state.status,"stale");
  assert.equal(awardDisplay(state,"first_dollar").verified,false);
  assert.equal(awardDisplay(state,"first_dollar").date,"");
  assert.equal(achievementState({schema:"penny-achievements-v1",status:"unavailable",achievements:[]},NOW).status,"unavailable");
});
test("reject duplicate, unknown, missing codes and inconsistent review dates",()=>{
  for(const change of [
    r=>r.achievements[0].code=r.achievements[1].code,
    r=>r.achievements[0].code="__proto__",
    r=>r.achievements.pop(),
    r=>r.achievements[0].status="earned",
    r=>r.achievements[0].review_day=null,
    r=>r.achievements[0].review_day=DAY+1,
    r=>r.achievements[0].review_day=DAY+86400,
    r=>r.achievements[1].review_day=DAY,
    r=>r.achievements[0].private="secret",
    r=>r.generated_at=NOW+1,
    r=>r.expires_at=NOW+3601,
    r=>r.private="secret",
  ]){
    const raw=fixture();change(raw);
    assert.equal(achievementState(raw,NOW).status,"unavailable");
  }
});
test("bounded parser refuses malformed and oversized input",()=>{
  assert.equal(parseAchievements("{",NOW).status,"unavailable");
  assert.equal(parseAchievements(" ".repeat(4097),NOW).status,"unavailable");
  assert.equal(parseAchievements(JSON.stringify(fixture()),NOW).status,"reviewed");
});
test("static achievement center contains no awarded fixtures and no network access",()=>{
  const html=readFileSync("website/index.html","utf8");
  const source=html.match(/<script type="application\/json" id="achievement-snapshot">([^<]+)<\/script>/);
  assert.ok(source);
  assert.deepEqual(JSON.parse(source[1]),{schema:"penny-achievements-v1",status:"unavailable",achievements:[]});
  assert.deepEqual([...html.matchAll(/data-achievement-code="([^"]+)"/g)].map(m=>m[1]),CODES);
  assert.equal([...html.matchAll(/data-award-status>Unverified/g)].length,3);
  assert.doesNotMatch(readFileSync("website/assets/achievements.mjs","utf8"),/\bfetch\s*\(|innerHTML\s*=/);
  assert.match(readFileSync("website/_headers","utf8"),/connect-src 'none'/);
});
