// Fixed development concepts only; no purchase, ownership or publication authority.
export const COLLECTION_VERSION = "office-concept-v1";
export const MUGS = Object.freeze([
  {
    "id": "mug-localhost-v1",
    "phrase": "There is no place like 127.0.0.1",
    "lines": [
      "There is no",
      "place like",
      "127.0.0.1"
    ],
    "color": "ivory"
  },
  {
    "id": "mug-sudo-coffee-v1",
    "phrase": "sudo make coffee",
    "lines": [
      "sudo",
      "make coffee"
    ],
    "color": "charcoal"
  },
  {
    "id": "mug-sleep-404-v1",
    "phrase": "404: Sleep Not Found",
    "lines": [
      "404:",
      "Sleep Not Found"
    ],
    "color": "sand"
  },
  {
    "id": "mug-cobol-v1",
    "phrase": "COBOL Never Dies",
    "lines": [
      "COBOL",
      "Never Dies"
    ],
    "color": "navy"
  },
  {
    "id": "mug-works-on-machine-v1",
    "phrase": "Works on My Machine",
    "lines": [
      "Works on",
      "My Machine"
    ],
    "color": "plum"
  },
  {
    "id": "mug-penny-slogan-v1",
    "phrase": "Financially Underfunded. Sarcastically Overqualified.",
    "lines": [
      "Financially",
      "Underfunded.",
      "Sarcastically",
      "Overqualified."
    ],
    "color": "sand"
  }
].map(m => Object.freeze({...m,lines:Object.freeze(m.lines)})));
export const SHIRTS = Object.freeze([
  {
    "id": "shirt-teal-v1",
    "color": "teal"
  },
  {
    "id": "shirt-plum-v1",
    "color": "plum"
  },
  {
    "id": "shirt-blue-v1",
    "color": "blue"
  },
  {
    "id": "shirt-forest-v1",
    "color": "forest"
  },
  {
    "id": "shirt-maroon-v1",
    "color": "maroon"
  },
  {
    "id": "shirt-mustard-v1",
    "color": "mustard"
  },
  {
    "id": "shirt-charcoal-v1",
    "color": "charcoal"
  }
].map(Object.freeze));

// Accept a trusted calendar date, not a browser clock. Date arithmetic uses
// UTC only as a stable civil-day index; timezone resolution happens upstream.
export function dailyStyle(date, shirtIds, mugIds) {
  try {
    if (typeof date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(date)
        || date < "2000-01-01" || date > "2099-12-31") return null;
    const stamp = Date.parse(date + "T00:00:00Z");
    if (!Number.isFinite(stamp) || new Date(stamp).toISOString().slice(0,10) !== date)
      return null;
    const valid = (ids, registry) => Array.isArray(ids) && ids.length > 0
      && ids.length <= registry.length && new Set(ids).size === ids.length
      && ids.every(id => registry.some(design => design.id === id));
    if (!valid(shirtIds, SHIRTS) || !valid(mugIds, MUGS)) return null;
    const day = Math.floor(stamp / 86400000);
    return Object.freeze({date,collectionVersion:COLLECTION_VERSION,
      shirtId:shirtIds[day % shirtIds.length],mugId:mugIds[day % mugIds.length]});
  } catch {
    console.error("Office collection date selection failed.");
    return null;
  }
}
