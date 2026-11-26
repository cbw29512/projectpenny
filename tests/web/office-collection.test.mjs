import test from "node:test";
import assert from "node:assert/strict";
import { MUGS, SHIRTS, dailyStyle } from "../../website/assets/scene/office-collection.mjs";
const shirts=SHIRTS.map(s=>s.id),mugs=MUGS.map(m=>m.id);

test("stable design IDs and exact readable localhost phrase",()=>{
  assert.equal(new Set([...shirts,...mugs]).size,shirts.length+mugs.length);
  const mug=MUGS.find(m=>m.id==="mug-localhost-v1");
  assert.equal(mug.lines.join(" "),mug.phrase);
  assert.equal(mug.phrase,"There is no place like 127.0.0.1");
  assert.ok(Object.isFrozen(mug.lines));
});

test("daily selection is repeatable and changes across consecutive dates including DST",()=>{
  const dates=["2026-03-07","2026-03-08","2026-03-09","2026-11-01","2026-11-02"];
  for(const date of dates) assert.deepEqual(dailyStyle(date,shirts,mugs),dailyStyle(date,shirts,mugs));
  for(const [a,b] of [[0,1],[1,2],[3,4]]) {
    assert.notEqual(dailyStyle(dates[a],shirts,mugs).shirtId,dailyStyle(dates[b],shirts,mugs).shirtId);
    assert.notEqual(dailyStyle(dates[a],shirts,mugs).mugId,dailyStyle(dates[b],shirts,mugs).mugId);
  }
  assert.ok(dailyStyle("2028-02-29",shirts,mugs));
});

test("refuses invalid dates, unknown or duplicate IDs and empty pools",()=>{
  for(const date of ["2026-02-30","2026-13-01","2026-11-1","2026-11-26T00:00:00Z",null])
    assert.equal(dailyStyle(date,shirts,mugs),null);
  assert.equal(dailyStyle("2026-11-26",[],mugs),null);
  assert.equal(dailyStyle("2026-11-26",shirts,["https://example.com"]),null);
  assert.equal(dailyStyle("2026-11-26",[shirts[0],shirts[0]],mugs),null);
  assert.equal(dailyStyle("2026-11-26",[shirts[0]],[mugs[0]]).mugId,mugs[0]);
});
