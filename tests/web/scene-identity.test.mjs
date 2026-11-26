import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

// Fixed preview baseline. Updating these pins requires Maker visual review.
const pins = Object.freeze({
  "website/assets/scene/room-v1.svg": "9e6ec806f4ff2165736dbcbf1b0563d9857c1513e572912cf7d1e61638b00a0e",
  "website/assets/scene/penny-v1.svg": "06d048aa3a15a66e9610ee3ceba8acd8cf0b4ea85b7d6184d68bfedf1b8e3e04",
  "website/assets/scene/desk-v1.svg": "a72a43536c3d4de2d52296c406785bb4683a408ea3d0ce8d5e94d7d6f27d5f14",
  "website/assets/scene/scene.css": "6f0b12574a6a124bea10f892580945fb5624cc927c9870810657355913020012"
});
const digest = bytes => createHash("sha256").update(bytes).digest("hex");
const read = path => readFileSync(new URL("../../" + path, import.meta.url));

test("character, room, desk and scene CSS retain exact pinned bytes", () => {
  for (const [path, expected] of Object.entries(pins)) {
    assert.equal(digest(read(path)), expected, path + " requires visual review");
  }
});

test("home uses a fixed ordered local scene, not model-selected artwork", () => {
  const html = read("website/index.html").toString("utf8");
  const scenes = html.match(/<div class="penny-scene"[^>]*>[\s\S]*?<\/div>/g);
  assert.equal(scenes?.length, 1);
  assert.equal(digest(scenes[0]), "a25c35b6701b1953abe0d134d230019f26acf986a15cc962553911ea4c2fd3a9");
  assert.match(html, /<link rel="stylesheet" href="\/assets\/scene\/scene\.css">/);
});

test("the layered preview preserves every original drawing element in order", () => {
  const original = read("website/assets/penny-preview.svg").toString("utf8");
  const inner = original.slice(original.indexOf('  <rect x="5"'), original.lastIndexOf("</svg>"));
  const layers = ["room-v1", "penny-v1", "desk-v1"].map(name => {
    const svg = read("website/assets/scene/" + name + ".svg").toString("utf8");
    return svg.slice(svg.indexOf("\n") + 1, svg.lastIndexOf("</svg>"));
  });
  assert.equal(layers.join(""), inner);
});

test("preview security policy does not allow remote images or inline script", () => {
  const headers = read("website/_headers").toString("utf8");
  const policy = headers.match(/Content-Security-Policy: ([^\n]+)/)?.[1];
  assert.ok(policy);
  const directives = Object.fromEntries(policy.split(";").map(part => {
    const [name, ...values] = part.trim().split(/\s+/);
    return [name, values];
  }));
  assert.deepEqual(directives["img-src"], ["'self'"]);
  assert.deepEqual(directives["script-src"], ["'self'"]);
  assert.deepEqual(directives["object-src"], ["'none'"]);
});
