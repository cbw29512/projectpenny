import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("Command Center has nine unavailable lanes and no fake tasks", () => {
  const html = readFileSync("website/index.html", "utf8");
  const start = html.indexOf('<section id="command-center"');
  const end = html.indexOf('<section id="vault"', start);
  assert.ok(start >= 0 && end > start);
  const board = html.slice(start, end);
  assert.equal([...board.matchAll(/data-board-lane="([^"]+)"/g)].length, 9);
  assert.equal([...board.matchAll(/No reviewed data available/g)].length, 9);
  assert.match(board, /No reviewed work board available/);
  assert.match(board, /id="community-idea"[^>]*maxlength="500"[^>]*disabled/);
  assert.match(board, /id="community-submit"[^>]*type="button"[^>]*disabled/);
  assert.doesNotMatch(board, /<form\b/i);
  assert.match(html, /href="#command-center"/);
});
