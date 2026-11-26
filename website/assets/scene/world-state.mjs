// A snapshot is presentation data, not publication authority. No HTML, CSS,
// arbitrary asset URL, coordinates, user information or financial data accepted.
export const DECOR = Object.freeze(["plant-v1", "mug-v1"]);
export const SLOTS = Object.freeze(["left-shelf", "right-shelf", "desk-corner"]);
export const OUTFIT = "plum-outfit-v1";
export const LAYERS = Object.freeze([OUTFIT,
  ...DECOR.flatMap(asset => SLOTS.map(slot => asset + ":" + slot))]);
const exact = (value, keys) => value !== null && typeof value === "object"
  && !Array.isArray(value) && Object.keys(value).length === keys.length
  && keys.every(key => Object.hasOwn(value, key));

export function parseWorld(text) {
  try {
    if (typeof text !== "string" || text.length > 2048) return null;
    const value = JSON.parse(text);
    if (!exact(value, ["schema", "status", "baseline", "revision", "placements", "outfit"])
      || value.schema !== "penny-world-v1" || value.status !== "reviewed_virtual_preview"
      || value.baseline !== "preview-v1" || !Number.isSafeInteger(value.revision)
      || value.revision < 0 || value.revision > 2048
      || (value.outfit !== null && value.outfit !== OUTFIT)
      || value.placements === null || typeof value.placements !== "object"
      || Array.isArray(value.placements)) return null;
    const used = new Set(), layers = [];
    for (const [asset, slot] of Object.entries(value.placements)) {
      if (!DECOR.includes(asset) || !SLOTS.includes(slot) || used.has(slot)) return null;
      used.add(slot);
      layers.push(asset + ":" + slot);
    }
    if (value.outfit !== null) layers.push(OUTFIT);
    // Each visible item requires at least acquisition and placement/equip.
    if (value.revision < layers.length * 2) return null;
    return Object.freeze({revision: value.revision, layers: Object.freeze(layers.sort())});
  } catch { return null; }
}

export function acceptWorld(previous, candidate) {
  if (!candidate || (previous && (candidate.revision < previous.revision ||
      (candidate.revision === previous.revision &&
       candidate.layers.join("|") !== previous.layers.join("|"))))) {
    return {state: previous, accepted: false};
  }
  return {state: candidate, accepted: true};
}
