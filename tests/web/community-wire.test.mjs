import test from "node:test";
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { validateSuggestion } from "../../netlify/community/state.mjs";
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
