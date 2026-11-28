import {stageLabel} from "./workshop-state.mjs";

// Timer redraws local state only: expiry and cooldown never trigger a request.
export function bindWorkshopReader({status,stage,updated,refresh},reader){
  let timer;
  function render(){
    clearTimeout(timer);
    const s=reader.snapshot(),v=s.state;
    stage.textContent=stageLabel(v);
    status.textContent=v.status==="reviewed"?"Reviewed historical Workshop snapshot":
      "No recent reviewed Workshop progress available.";
    updated.textContent=v.generatedAt===null?"No verified update timestamp.":
      "Reviewed snapshot generated: "+new Date(v.generatedAt*1000).toISOString();
    refresh.disabled=!s.canRefresh;
    refresh.textContent=s.busy?"Checking progress…":"Check Workshop progress";
    if(!s.closed){
      const now=Date.now(),times=[];
      if(v.status==="reviewed")times.push(v.expiresAt*1000);
      if(!s.busy&&!s.canRefresh&&Number.isFinite(s.refreshAt))times.push(s.refreshAt);
      const next=Math.min(...times.filter(t=>t>now));
      if(Number.isFinite(next))timer=setTimeout(render,Math.max(1,next-now));
    }
  }
  refresh.addEventListener("click",async()=>{
    try{const pending=reader.read();render();await pending;render();}
    catch{reader.close();render();console.error("Workshop display unavailable.");}
  });
  render();
  return Object.freeze({render,close:()=>{reader.close();render();}});
}
