import test from "node:test";
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { validateSuggestion, validateClaim } from "../../netlify/community/state.mjs";
import { route } from "../../netlify/gateway/state.mjs";

test("community envelope accepts bounded ideas only", () => {
  const key = randomUUID();
  assert.equal(validateSuggestion({key,text:"Make a useful calendar"}),true);
  for (const text of ["", "!!", "a".repeat(501), "idea\u200b", "idea\n", "\ufb03".repeat(200), "idea\ud800"])
    assert.equal(validateSuggestion({key,text}),false);
  for (const extra of [{owner:key},{tier:6},{command:"run"},{role:"admin"}])
    assert.equal(validateSuggestion({key,text:"Useful idea",...extra}),false);
  assert.equal(validateSuggestion({key:"not-uuid",text:"Useful idea"}),false);
  assert.equal(validateSuggestion(null),false);
});

test("community candidate does not activate the conversation gateway", () => {
  assert.equal(route("POST","/api/v1/suggestions"),null);
});

test("community claim rejects stale leases, excessive lifetime and authority fields", () => {
  const now = 1800000000;
  const claim = {id:randomUUID(),owner:randomUUID(),key:randomUUID(),
    text:"Build a useful calendar",fence:randomUUID(),expiresAt:now+3600,leaseUntil:now+900};
  assert.equal(validateClaim(claim,now),true);
  for (const change of [
    {leaseUntil:now}, {leaseUntil:now+901}, {expiresAt:now+3601},
    {expiresAt:now+899}, {leaseUntil:now+0.5}, {owner:"admin"},
    {fence:"00000000-0000-0000-0000-000000000000"}, {role:"admin"},
    {text:"x".repeat(501)}, {expiresAt:Infinity}
  ]) assert.equal(validateClaim({...claim,...change},now),false);
  assert.equal(validateClaim(claim,NaN),false);
  assert.equal(validateClaim(claim,now+900),false);
});
