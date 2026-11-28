import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {progressState,parseProgress,metricText,usd} from "../../website/assets/progress-state.mjs";

const NOW=1700000000;
function fixture() {
  return {status:"reviewed",version:1,generated_at:NOW-10,expires_at:NOW+50,
    payload:{schema:"penny-progress-v1",
      finance:{commercial_receipts:1000,commercial_refunds:100,community_support:200,
        founder_cash_funding:500,founder_paid_costs:300,operating_expenses:300,
        payment_fees:50,commercial_result_after_recorded_costs:550,matched_cash:1550,
        statement_at:NOW-100},
      business:{proposed:0,approved:0,started:0,overdue:0,expired:0,rejected:0,
        stopped:1,measured_target_met:2,measured_target_missed:1}}};
}
test("reviewed counts and exact financial cents, including zero and loss",()=>{
  const raw=fixture();
  const state=progressState(raw,NOW);
  assert.equal(state.status,"reviewed");
  assert.equal(metricText(state,"finance","matched_cash"),"$15.50");
  assert.equal(metricText(state,"business","proposed"),"0");
  assert.equal(metricText(state,"business","measured_target_missed"),"1");
  assert.equal(usd(-123), "-$1.23");
  assert.equal(usd(8999999999999999),"$89,999,999,999,999.99");
});
test("missing sections and stale snapshots never display figures",()=>{
  const raw=fixture();
  raw.payload.finance=null;
  assert.equal(metricText(progressState(raw,NOW),"finance","matched_cash"),"Unavailable");
  const stale=progressState(fixture(),NOW+50);
  assert.equal(stale.status,"stale");
  assert.equal(stale.finance,null);
  assert.equal(metricText(stale,"business","stopped"),"Unavailable");
  assert.equal(progressState({status:"unavailable",payload:null},NOW).status,"unavailable");
});
test("strict allowlist rejects private or malformed values",()=>{
  for (const modify of [
    r=>r.payload.finance.private="secret",
    r=>r.payload.business.measured_target_missed=true,
    r=>r.payload.finance.matched_cash=-1,
    r=>r.payload.finance.matched_cash=Number.MAX_SAFE_INTEGER+1,
    r=>r.payload.finance.statement_at=NOW+1,
    r=>r.payload.finance.statement_at=NOW-86401,
    r=>r.expires_at=NOW+7200,
    r=>r.generated_at=NOW+1,
    r=>r.payload.schema="unexpected",
  ]) {
    const raw=fixture(); modify(raw);
    assert.equal(progressState(raw,NOW).status,"unavailable");
  }
  assert.equal(parseProgress("{",NOW).status,"unavailable");
  assert.equal(parseProgress(" ".repeat(8193),NOW).status,"unavailable");
});
test("static website ships no financial fixture or network access",()=>{
  const html=readFileSync("website/index.html","utf8");
  const source=html.match(/<script type="application\/json" id="progress-snapshot">([^<]+)<\/script>/);
  assert.ok(source);
  assert.deepEqual(JSON.parse(source[1]),{status:"unavailable",payload:null});
  const fields=[...html.matchAll(/data-progress-scope="(finance|business)" data-progress-key="([^"]+)">Unavailable/g)];
  assert.equal(fields.length,18);
  for (const [,scope,key] of fields) assert.ok(Object.hasOwn(fixture().payload[scope],key));
  assert.equal(new Set(fields.map(x=>x[1]+":"+x[2])).size,18);
  assert.match(readFileSync("website/_headers","utf8"),/connect-src 'none'/);
  assert.doesNotMatch(readFileSync("website/assets/progress.mjs","utf8"),/\bfetch\s*\(|innerHTML\s*=/);
});
