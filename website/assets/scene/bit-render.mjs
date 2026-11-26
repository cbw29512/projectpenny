import { bitReaction } from "./bit-state.mjs";
import { parseRest } from "./night-state.mjs";
const MODES=Object.freeze(["idle","attentive","celebrating","confused","charging"]);
const ART=Object.freeze(Object.fromEntries(MODES.map(m=>[m,"/assets/scene/bit/bit-"+m+"-v1.svg"])));
export function updateBit(node,text,now,restText){
  try{
    const rest=parseRest(restText,now);
    const mode=node.hidden?"idle":rest?.state==="asleep"?"charging":bitReaction(text,now);
    node.src=ART[mode];
    node.dataset.bitMode=mode;
    return mode;
  }catch{console.error("Bit presentation unavailable.");return "idle";}
}
function boot(){
  const node=document.getElementById("bit-companion");
  const source=document.getElementById("bit-activity-snapshot");
  if(!node||!source)return;
  let timer;
  const refresh=()=>{
    clearTimeout(timer);
    if(document.visibilityState==="hidden"||node.hidden)return;
    updateBit(node,source.textContent,Math.floor(Date.now()/1000),document.getElementById("rest-snapshot")?.textContent);
    timer=setTimeout(refresh,5000);
  };
  new MutationObserver(refresh).observe(node,{attributes:true,attributeFilter:["hidden"]});
  window.addEventListener("pageshow",refresh);
  window.addEventListener("pagehide",()=>clearTimeout(timer));
  document.addEventListener("visibilitychange",refresh);
  refresh();
}
try{if(typeof document!=="undefined")boot();}
catch{console.error("Bit initialization failed.");}
