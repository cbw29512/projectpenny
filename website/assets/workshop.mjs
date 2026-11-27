import {parseWorkshop,stageLabel} from "./workshop-state.mjs";

function boot(){
  const source=document.getElementById("workshop-snapshot");
  const status=document.getElementById("workshop-status");
  const stage=document.getElementById("packing-stage");
  const updated=document.getElementById("workshop-updated");
  if(!source||!status||!stage||!updated)return;
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
