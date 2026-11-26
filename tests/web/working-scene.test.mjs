import test from "node:test";
import assert from "node:assert/strict";

test("disconnected preview preserves drafts without invented thoughts or speech", async () => {
  const makeTarget = (fields = {}) => {
    const handlers = new Map();
    return Object.assign({
      addEventListener: (type, fn) => handlers.set(type, fn),
      fire: type => handlers.get(type)?.(),
    }, fields);
  };
  const question = makeTarget({ value: "draft", disabled: true });
  const thought = makeTarget({ textContent: "No verified activity feed is connected yet." });
  const welcome = makeTarget({ textContent: "Live responses are not connected." });
  const send = makeTarget({ disabled: true });
  const notice = makeTarget();
  const elements = { question, thought, welcome, "preview-send": send, notice, count: makeTarget() };
  const doc = makeTarget({ hidden: false, getElementById: id => elements[id] });
  const win = makeTarget({
    setTimeout: () => assert.fail("No fictional activity timer"),
    matchMedia: () => assert.fail("No scripted thought animation"),
  });
  const oldDoc = globalThis.document;
  const oldWin = globalThis.window;
  try {
    globalThis.document = doc;
    globalThis.window = win;
    await import("../../website/assets/home.mjs");
    assert.equal(question.disabled, false);
    assert.equal(send.disabled, false);
    send.fire("click");
    assert.equal(question.value, "draft");
    assert.equal(thought.textContent, "No verified activity feed is connected yet.");
    assert.equal(welcome.textContent, "Live responses are not connected.");
    doc.hidden = true;
    doc.fire("visibilitychange");
    doc.hidden = false;
    doc.fire("visibilitychange");
    assert.equal(thought.textContent, "No verified activity feed is connected yet.");
  } finally {
    if (oldDoc === undefined) delete globalThis.document;
    else globalThis.document = oldDoc;
    if (oldWin === undefined) delete globalThis.window;
    else globalThis.window = oldWin;
  }
});
