import { MUGS, SHIRTS } from "./office-collection.mjs";
import { POSTERS } from "./office-posters.mjs";

function boot() {
  const grid = document.getElementById("collection-mugs");
  const palette = document.getElementById("collection-shirts");
  const notice = document.getElementById("collection-notice");
  const posters = document.getElementById("collection-posters");
  if (!grid || !palette || !posters || !notice) return;
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
    const details = document.createElement("details");
    details.dataset.designId = shirt.id;
    const summary = document.createElement("summary");
    summary.textContent = shirt.name + " · " + shirt.phrase;
    const picture = document.createElement("div");
    picture.classList.add("shirt-concept", shirt.color);
    picture.setAttribute("aria-hidden", "true");
    const print = document.createElement("div");
    for (const line of shirt.lines) {
      const span = document.createElement("span");
      span.textContent = line;
      print.append(span);
    }
    const credit = document.createElement("small");
    credit.textContent = "PROJECT PENNY";
    print.append(credit);
    picture.append(print);
    const text = document.createElement("p");
    text.textContent = "Concept only — not available for purchase.";
    details.append(summary, picture, text);
    return details;
  });
  const wallArt = POSTERS.map(poster => {
    const details = document.createElement("details");
    details.dataset.designId = poster.id;
    const summary = document.createElement("summary");
    summary.textContent = poster.title + " · " + poster.phrase;
    const picture = document.createElement("div");
    picture.classList.add("poster-concept", poster.theme);
    picture.setAttribute("aria-hidden", "true");
    const symbol = document.createElement("span");
    symbol.className = "poster-symbol";
    symbol.textContent = poster.symbol;
    const title = document.createElement("strong");
    title.textContent = poster.title;
    picture.append(symbol, title);
    for (const line of poster.lines) {
      const span = document.createElement("span");
      span.textContent = line;
      picture.append(span);
    }
    const credit = document.createElement("small");
    credit.textContent = "PROJECT PENNY";
    picture.append(credit);
    const note = document.createElement("p");
    note.textContent = "Wall art concept only — not available for purchase.";
    details.append(summary, picture, note);
    return details;
  });
  posters.replaceChildren(...wallArt);
  grid.replaceChildren(...cards);
  palette.replaceChildren(...colors);
  notice.textContent = "Proposed designs only. No store or live daily selection is connected.";
}
try { if (typeof document !== "undefined") boot(); }
catch { console.error("Office collection preview unavailable."); }
