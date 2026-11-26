import { MUGS, SHIRTS } from "./office-collection.mjs";

function boot() {
  const grid = document.getElementById("collection-mugs");
  const palette = document.getElementById("collection-shirts");
  const notice = document.getElementById("collection-notice");
  if (!grid || !palette || !notice) return;
  // Only fixed registry strings and static CSS classes; never user/model HTML.
  const cards = MUGS.map(mug => {
    const details = document.createElement("details");
    details.dataset.designId = mug.id;
    const summary = document.createElement("summary");
    summary.textContent = mug.phrase;
    const picture = document.createElement("div");
    picture.classList.add("mug-concept", mug.color);
    picture.setAttribute("aria-hidden","true");
    for (const line of mug.lines) {
      const span = document.createElement("span");
      span.textContent = line;
      picture.append(span);
    }
    const credit = document.createElement("small");
    credit.textContent = "PROJECT PENNY";
    picture.append(credit);
    const text = document.createElement("p");
    text.textContent = "Concept only — not available for purchase.";
    details.append(summary,picture,text);
    return details;
  });
  const colors = SHIRTS.map(shirt => {
    const item = document.createElement("li");
    item.dataset.designId = shirt.id;
    item.textContent = shirt.color;
    return item;
  });
  grid.replaceChildren(...cards);
  palette.replaceChildren(...colors);
  notice.textContent = "Proposed designs only. No store or live daily selection is connected.";
}
try { if (typeof document !== "undefined") boot(); }
catch { console.error("Office collection preview unavailable."); }
