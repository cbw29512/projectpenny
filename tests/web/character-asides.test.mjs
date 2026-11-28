import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import { nextAside } from "../../website/assets/character-asides.mjs";

test("scripted asides cycle deterministically without visitor data", () => {
  const seen = new Set();
  let index = 0;
  for (let i = 0; i < 5; i++) {
    const result = nextAside(index);
    assert.equal(typeof result.text, "string");
    assert.ok(result.text.length > 0);
    assert.ok(Object.isFrozen(result));
    seen.add(result.text);
    index = result.index;
  }
  assert.equal(index, 0);
  assert.equal(seen.size, 5);
  assert.deepEqual(nextAside(0), nextAside(0));
});

test("invalid aside state fails closed", () => {
  for (const value of [-1, 5, NaN, 0.1, "0", null, {}]) {
    assert.throws(() => nextAside(value), RangeError);
  }
});

test("homepage does not invent live thought or speech", () => {
  const html = readFileSync(new URL("../../website/index.html", import.meta.url), "utf8");
  const css = readFileSync(new URL("../../website/assets/world.css", import.meta.url), "utf8");
  const home = readFileSync(new URL("../../website/assets/home.mjs", import.meta.url), "utf8");
  assert.match(html, /class="thought-bubble" aria-labelledby="thought-label"/);
  assert.match(html, /PENNY THINKS · VERIFIED ACTIVITY ONLY/);
  assert.match(html, /class="bubble" aria-labelledby="speech-label"/);
  assert.match(html, /PENNY SAYS · LIVE OUTPUT UNAVAILABLE/);
  assert.match(html, /not internal AI reasoning/);
  assert.match(css, /\.thought-bubble\s*\{[^}]*dashed/);
  assert.doesNotMatch(home, /nextAside|rotateAside/);
  assert.doesNotMatch(home, /\.innerHTML\s*=|localStorage|sessionStorage/);
});

test("actual homepage preview boot and interaction never use the network", () => {
  const source = readFileSync(new URL("../../website/assets/home.mjs", import.meta.url), "utf8");
  const events = {};
  const question = { value: "A visitor question", addEventListener: (name, fn) => events[name] = fn };
  const send = { addEventListener: (name, fn) => events["send:" + name] = fn };
  const notice = {}, count = {};
  const nodes = { "home-conversation": { dataset: { live: "false" } }, question, count, notice, "preview-send": send };
  let networkCalls = 0, liveCalls = 0, errors = 0;
  const state = { length: 18, canPreview: true, notice: "Local preview" };
  // Execute the actual entrypoint with injected imports and a minimal DOM.
  runInNewContext(source.replace(/^import .*;\s*$/gm, ""), {
    document: { getElementById: id => nodes[id] },
    fetch: () => { networkCalls++; throw Error("Unexpected network"); },
    bindHomeConversation: () => { liveCalls++; throw Error("Unexpected live mode"); },
    MAX_QUESTION: 500, PREVIEW_NOTICE: "Local preview",
    questionState: () => state, previewQuestion: () => state,
    console: { error: () => errors++ }
  });
  assert.equal(question.disabled, false);
  events.input();
  events["send:click"]();
  assert.equal(notice.textContent, "Local preview");
  assert.equal(networkCalls, 0);
  assert.equal(liveCalls, 0);
  assert.equal(errors, 0);
});
