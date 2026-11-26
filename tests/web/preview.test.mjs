import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { questionState, previewQuestion, MAX_QUESTION } from "../../website/assets/preview-state.mjs";

test("empty and whitespace drafts cannot be previewed", () => {
  assert.equal(questionState("").canPreview,false);
  assert.equal(questionState("   ").canPreview,false);
});
test("question limit matches the UI and rejects oversized input", () => {
  assert.equal(MAX_QUESTION,2000);
  assert.equal(questionState("a".repeat(2000)).canPreview,true);
  assert.equal(questionState("a".repeat(2001)).canPreview,false);
  assert.throws(() => questionState({text:"hello"}),TypeError);
});
test("preview never claims a message was submitted or returns input as markup", () => {
  const draft = "<script>alert(1)</script>";
  const state = previewQuestion(draft);
  assert.equal(state.length,draft.length);
  assert.match(state.notice,/not sent/);
  assert.equal(JSON.stringify(state).includes(draft),false);
  assert.equal(Object.isFrozen(state),true);
});
test("home has all primary sections and fail-closed initial controls", () => {
  const html = readFileSync("website/index.html","utf8");
  for (const id of ["home","question","preview-send","progress","vault","council","diary"]) {
    assert.ok(html.includes('id="'+id+'"'));
  }
  assert.match(html,/id="question"[^>]*maxlength="2000"[^>]*disabled/);
  assert.match(html,/id="preview-send"[^>]*type="button"[^>]*disabled/);
  assert.match(html,/Live AI not connected/);
  assert.doesNotMatch(html,/<form\b/i);
});
test("static preview CSP blocks network calls and form submission", () => {
  const headers = readFileSync("website/_headers","utf8");
  assert.match(headers,/connect-src 'none'/);
  assert.match(headers,/form-action 'none'/);
  assert.match(headers,/frame-ancestors 'none'/);
  assert.match(headers,/X-Robots-Tag: noindex/);
  assert.match(readFileSync("netlify.toml","utf8"),/publish = "website"/);
});
