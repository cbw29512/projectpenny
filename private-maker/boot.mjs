import {createMakerClient} from "./client.mjs";
import {bindMaker} from "./view.mjs";
try{
  if(location.protocol!=="https:"||!globalThis.isSecureContext)throw Error("Secure origin required");
  const nodes=Object.fromEntries(["token","load","clear","read","confirm","pause","admission","pending","processing","notice"]
    .map(id=>[id,document.getElementById("maker-"+id)]));
  if(Object.values(nodes).some(n=>!n))throw Error("Missing console controls");
  const client=createMakerClient({enabled:true,fetcher:(path,opts)=>fetch(path,opts),clock:()=>Date.now()});
  const view=bindMaker(nodes,client);
  let timer;
  function tick(){
    clearTimeout(timer);
    if(document.visibilityState==="hidden")return;
    view.render();timer=setTimeout(tick,1000);
  }
  document.addEventListener("visibilitychange",tick);
  window.addEventListener("pagehide",()=>{clearTimeout(timer);view.close();});
  tick();
}catch{
  console.error("Maker console initialization refused.");
  const notice=document.getElementById("maker-notice");
  if(notice)notice.textContent="Maker console unavailable. Authorized HTTPS host required.";
}
