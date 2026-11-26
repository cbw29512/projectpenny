import { activityView } from "./activity-state.mjs";
export function renderActivity(label,thought,text,now){
  try{
    const [status,copy]=activityView(text,now);
    label.textContent=status;thought.textContent=copy;
  }catch{console.error("Activity display unavailable.");}
}
function boot(){
  const get=id=>document.getElementById(id);
  const label=get("activity-label"),thought=get("thought"),source=get("activity-snapshot");
  if(!label||!thought||!source)return;
  let timer;
  const refresh=()=>{
    clearTimeout(timer);
    if(document.visibilityState==="hidden")return;
    renderActivity(label,thought,source.textContent,Math.floor(Date.now()/1000));
    timer=setTimeout(refresh,1000);
  };
  window.addEventListener("pageshow",refresh);
  window.addEventListener("pagehide",()=>clearTimeout(timer));
  document.addEventListener("visibilitychange",refresh);
  refresh();
}
try{if(typeof document!=="undefined")boot();}
catch{console.error("Activity initialization failed.");}
