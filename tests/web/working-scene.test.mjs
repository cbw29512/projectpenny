import test from "node:test";
import assert from "node:assert/strict";

test("working scene rotates only while visible and leaves speech and draft alone", async () => {
  const makeTarget = (fields = {}) => {
    const handlers = new Map();
    return Object.assign({
      addEventListener: (type, fn) => handlers.set(type, fn),
      fire: type => handlers.get(type)?.(),
    }, fields);
  };
  const question = makeTarget({ value: "draft", disabled: true });
  const thought = makeTarget({ textContent: "initial" });
  const welcome = makeTarget({ textContent: "speech" });
  const pause = makeTarget({ hidden: true });
  const send = makeTarget({ disabled: true });
  const notice = makeTarget();
  const motion = makeTarget({ matches: false });
  const elements = { question, thought, welcome, "pause-asides": pause,
    "preview-send": send, notice, count: makeTarget() };
  let nextId = 0;
  const timers = new Map();
  const doc = makeTarget({ hidden: false, getElementById: id => elements[id] });
  const win = makeTarget({
    matchMedia: () => motion,
    setTimeout: (fn, delay) => {
      assert.equal(delay, 15000);
      timers.set(++nextId, fn);
      return nextId;
    },
    clearTimeout: id => timers.delete(id),
  });
  const tick = () => {
    assert.equal(timers.size, 1);
    const [id, fn] = timers.entries().next().value;
    timers.delete(id);
    fn();
  };
  const oldDoc = globalThis.document;
  const oldWin = globalThis.window;
  try {
    globalThis.document = doc;
    globalThis.window = win;
    await import("../../website/assets/home.mjs");
    assert.equal(question.disabled, false);
    assert.equal(send.disabled, false);
    tick();
    assert.notEqual(thought.textContent, "initial");
    assert.equal(question.value, "draft");
    assert.equal(welcome.textContent, "speech");
    doc.hidden = true;
    doc.fire("visibilitychange");
    assert.equal(timers.size, 0);
    doc.hidden = false;
    doc.fire("visibilitychange");
    assert.equal(timers.size, 1);
    pause.fire("click");
    assert.equal(timers.size, 0);
    const stopped = thought.textContent;
    send.fire("click");
    assert.equal(thought.textContent, stopped);
    pause.fire("click");
    assert.equal(timers.size, 1);
    motion.matches = true;
    motion.fire("change");
    assert.equal(timers.size, 0);
    assert.equal(pause.hidden, true);
    motion.matches = false;
    motion.fire("change");
    win.fire("pagehide");
    assert.equal(timers.size, 0);
    win.fire("pageshow");
    assert.equal(timers.size, 1);
  } finally {
    if (oldDoc === undefined) delete globalThis.document;
    else globalThis.document = oldDoc;
    if (oldWin === undefined) delete globalThis.window;
    else globalThis.window = oldWin;
  }
});
