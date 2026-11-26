import { MUGS, SHIRTS, dailyStyle } from "./office-collection.mjs";
import { POSTERS } from "./office-posters.mjs";

export const OFFICE_VERSION = "office-concept-v3";
export const POSTER_IDS = Object.freeze(POSTERS.map(p => p.id));
const SHIRT_IDS = Object.freeze(SHIRTS.map(s => s.id));
const MUG_IDS = Object.freeze(MUGS.map(m => m.id));

// Extend the existing v2 schedule without rewriting its historical output.
export function dailyOfficeStyle(date, shirts=SHIRT_IDS, mugs=MUG_IDS, posters=POSTER_IDS) {
  try {
    const base = dailyStyle(date, shirts, mugs);
    if (!base || !Array.isArray(posters) || !posters.length
        || posters.length > POSTER_IDS.length || new Set(posters).size !== posters.length
        || !posters.every(id => POSTER_IDS.includes(id))) return null;
    const day = Math.floor(Date.parse(date + "T00:00:00Z") / 86400000);
    return Object.freeze({...base, collectionVersion:OFFICE_VERSION,
      posterId:posters[day % posters.length]});
  } catch { console.error("Daily office selection failed."); return null; }
}

// Exact reviewed record only. Transport and Maker approval are external gates.
// Do not infer authority from the browser clock or accept any arbitrary strings.
export function parseDailyOffice(text) {
  try {
    if (typeof text !== "string" || text.length > 2048) return null;
    const s = JSON.parse(text);
    const keys = ["schema","status","date","collectionVersion","shirtId","mugId","posterId"];
    if (!s || typeof s !== "object" || Array.isArray(s)
        || Object.keys(s).length !== keys.length || !keys.every(k=>Object.hasOwn(s,k))
        || s.schema !== "penny-daily-office-v1" || s.status !== "reviewed_virtual_preview"
        || s.collectionVersion !== OFFICE_VERSION
        || !dailyOfficeStyle(s.date,[s.shirtId],[s.mugId],[s.posterId])) return null;
    return Object.freeze({date:s.date,collectionVersion:s.collectionVersion,
      shirtId:s.shirtId,mugId:s.mugId,posterId:s.posterId});
  } catch { return null; }
}

export function acceptDailyOffice(previous, candidate) {
  if (!candidate || (previous && (candidate.date < previous.date ||
      (candidate.date === previous.date && ["shirtId","mugId","posterId","collectionVersion"]
        .some(k => previous[k] !== candidate[k]))))) return null;
  return candidate;
}

export function describeOffice(style) {
  try {
    if (!style || style.collectionVersion !== OFFICE_VERSION) return null;
    const shirt=SHIRTS.find(s=>s.id===style.shirtId);
    const mug=MUGS.find(m=>m.id===style.mugId);
    const poster=POSTERS.find(p=>p.id===style.posterId);
    if (!shirt || !mug || !poster) return null;
    return {shirt,mug,poster};
  } catch { return null; }
}
