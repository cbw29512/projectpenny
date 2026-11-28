import {parseWorkshop,stageLabel} from "./workshop-state.mjs";
import {createWorkshopReader} from "./workshop-reader.mjs";
import {bindWorkshopReader} from "./workshop-reader-render.mjs";

function boot(){
  const source=document.getElementById("workshop-snapshot");
  const status=document.getElementById("workshop-status");
  const stage=document.getElementById("packing-stage");
  const updated=document.getElementById("workshop-updated");
  if(!source||!status||!stage||!updated)return;
  const refresh=document.getElementById("workshop-refresh");
  // Production must explicitly change both this flag and the CSP after review.
  if(refresh&&refresh.dataset.live==="true"){
    const reader=createWorkshopReader({enabled:true,fetcher:globalThis.fetch.bind(globalThis),clock:Date.now});
    const view=bindWorkshopReader({status,stage,updated,refresh},reader);
    window.addEventListener("pageshow",view.render);
    document.addEventListener("visibilitychange",()=>{if(document.visibilityState==="visible")view.render();});
    return;
  }
  let timer;
  const render=()=>{
    clearTimeout(timer);
    const state=parseWorkshop(source.textContent,Math.floor(Date.now()/1000));
    stage.textContent=stageLabel(state);
    status.textContent=state.status==="reviewed"?"Reviewed historical Workshop snapshot":
      state.status==="stale"?"Workshop snapshot expired — progress hidden":
      "No reviewed Workshop progress available. Live product data is not connected.";
    updated.textContent=state.generatedAt===null?"No verified update timestamp.":
      "Reviewed snapshot generated: "+new Date(state.generatedAt*1000).toISOString();
    if(state.status==="reviewed")timer=setTimeout(render,Math.max(1,state.expiresAt*1000-Date.now()));
  };
  render();
  window.addEventListener("pageshow",render);
  document.addEventListener("visibilitychange",()=>{
    if(document.visibilityState==="visible")render();
  });
}
try{boot();}catch{console.error("Penny Workshop display unavailable.");}
