import { dailyOfficeStyle, parseDailyOffice, acceptDailyOffice, describeOffice } from "./daily-office.mjs";
import { POSTERS } from "./office-posters.mjs";

// A registered local asset map; never use snapshot text as a URL.
const ART = new Map(POSTERS.map(p=>[p.id,"/assets/scene/posters/"+p.id+".svg"]));

export function officePresenter(frame, links, notice) {
  let reviewed = null;
  function show(style, demo) {
    const design=describeOffice(style);
    if (!design || !ART.has(design.poster.id)) return false;
    frame.src=ART.get(design.poster.id);
    frame.hidden=false;
    for (const kind of ["shirt","mug","poster"]) {
      const item=design[kind];
      links[kind].textContent=item.phrase;
      // IDs originate in the immutable catalog, not model or input strings.
      links[kind].href="#design-"+item.id;
    }
    notice.textContent=(demo?"Date preview (not live) · ":"Reviewed daily concept · ")
      +style.date+" · Shirt and mug shown as design links; wall poster shown in scene.";
    return true;
  }
  return {
    review(text) {
      try {
        const next=acceptDailyOffice(reviewed,parseDailyOffice(text));
        if (!next) {
          if (reviewed) { show(reviewed,false); notice.textContent+=" · Update unavailable."; }
          return false;
        }
        if (!show(next,false)) return false;
        reviewed=next;
        return true;
      } catch { console.error("Daily office review unavailable."); return false; }
    },
    preview(date) {
      try {
        if (reviewed) return false;
        const sample=dailyOfficeStyle(date);
        return sample ? show(sample,true) : false;
      } catch { console.error("Daily office date preview failed."); return false; }
    }
  };
}
function boot() {
  const get=id=>document.getElementById(id);
  const frame=get("daily-poster-frame"),notice=get("daily-office-status");
  const input=get("daily-office-date"),button=get("daily-office-preview");
  const source=get("daily-office-snapshot");
  const links={shirt:get("daily-shirt-link"),mug:get("daily-mug-link"),poster:get("daily-poster-link")};
  if (!frame||!notice||!input||!button||!source||Object.values(links).some(x=>!x)) return;
  const presenter=officePresenter(frame,links,notice);
  const refresh=()=>{
    if (presenter.review(source.textContent)) { input.disabled=true; button.disabled=true; }
  };
  button.addEventListener("click",()=> {
    if (!presenter.preview(input.value)) notice.textContent="Date preview unavailable.";
  });
  document.addEventListener("click",event=>{
    const link=Object.values(links).find(node=>node===event.target);
    if (!link) return;
    const target=document.getElementById(link.hash.slice(1));
    if (target && target.tagName==="DETAILS") target.open=true;
  });
  window.addEventListener("pageshow",refresh);
  refresh();
}
try { if (typeof document !== "undefined") boot(); }
catch { console.error("Daily office initialization failed."); }
