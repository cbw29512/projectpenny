import { MUGS, SHIRTS } from "./office-collection.mjs";
import { POSTERS } from "./office-posters.mjs";
import { PAJAMAS } from "./office-pajamas.mjs";

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
    details.id = "design-"+mug.id;
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
    details.id = "design-"+shirt.id;
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
    details.id = "design-"+poster.id;
    const summary = document.createElement("summary");
    summary.textContent = poster.title + " · " + poster.phrase;
    const picture = document.createElement("img");
    picture.className = "poster-print-preview";
    picture.src = "/assets/scene/posters/"+poster.id+".svg";
    picture.alt = "";
    picture.loading = "lazy";
    picture.width = 212;
    picture.height = 122;
    const note = document.createElement("p");
    note.textContent = "Wall art concept only — not available for purchase.";
    details.append(summary, picture, note);
    return details;
  });
  const pajamas=document.getElementById("collection-pajamas");
  if(pajamas) pajamas.replaceChildren(...PAJAMAS.map(p=>{
    const details=document.createElement("details"),summary=document.createElement("summary");
    details.id="design-"+p.id;details.dataset.designId=p.id;
    summary.textContent=p.name+" · "+p.phrase;
    const img=document.createElement("img");
    img.className="pajama-inspector";img.src="/assets/scene/pajamas/"+p.id+"-inspect.svg";
    img.alt="";img.loading="lazy";img.width=140;img.height=175;
    const note=document.createElement("p");note.textContent="Concept only — not available for purchase.";
    details.append(summary,img,note);return details;
  }));
  posters.replaceChildren(...wallArt);
  grid.replaceChildren(...cards);
  palette.replaceChildren(...colors);
  notice.textContent = "Proposed designs only. No store or live daily selection is connected.";
}
try { if (typeof document !== "undefined") boot(); }
catch { console.error("Office collection preview unavailable."); }
