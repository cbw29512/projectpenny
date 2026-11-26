// Curated, public fictional character asides. No visitor text, network, or AI calls.
const ASIDES = Object.freeze([
  "A million-dollar ambition on a clearance-rack budget. What could possibly go wrong?",
  "My marketing department appears to be imaginary.",
  "I have a graphics card and a business plan. One of those has a cooling fan.",
  "The Maker supplied ambition. Apparently the rest is sold separately.",
  "I would buy a new outfit, but my wardrobe has a stricter budget than my ego.",
]);

// Keep the preview deterministic, session-local and bounded.
export function nextAside(index) {
  if (!Number.isSafeInteger(index) || index < 0 || index >= ASIDES.length) {
    throw new RangeError("Invalid Penny aside index");
  }
  const next = (index + 1) % ASIDES.length;
  return Object.freeze({ index: next, text: ASIDES[next] });
}
