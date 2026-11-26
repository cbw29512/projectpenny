import {parseAchievements,awardDisplay} from "./achievement-state.mjs";

function boot() {
  const source=document.getElementById("achievement-snapshot");
  const notice=document.getElementById("achievement-status");
  if(!source||!notice) return;
  const cards=[...document.querySelectorAll("[data-achievement-code]")];
  let timer;
  const render=()=>{
    clearTimeout(timer);
    const state=parseAchievements(source.textContent,Math.floor(Date.now()/1000));
    for(const card of cards) {
      const label=card.querySelector("[data-award-status]");
      const date=card.querySelector("[data-award-date]");
      if(!label||!date) continue;
      const display=awardDisplay(state,card.dataset.achievementCode);
      label.textContent=display.label;
      card.classList.toggle("achievement-verified",display.verified);
      date.hidden=!display.verified;
      date.textContent=display.verified?"Reviewed "+display.date+" (UTC)":"";
    }
    notice.textContent=state.status==="reviewed"?
      "Reviewed achievements. Verification depends on current evidence.":
      state.status==="stale"?"Achievement snapshot expired — verification hidden.":
      "No reviewed achievement snapshot available.";
    if(state.status==="reviewed")
      timer=setTimeout(render,Math.max(1,state.expiresAt*1000-Date.now()));
  };
  window.addEventListener("pageshow",render);
  document.addEventListener("visibilitychange",()=>{
    if(document.visibilityState==="visible") render();
  });
  render();
}
try { boot(); }
catch { console.error("Penny achievement initialization failed."); }
