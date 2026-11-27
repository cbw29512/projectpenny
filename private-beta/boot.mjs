import {createBetaMailbox} from "../website/assets/beta-mailbox.mjs";
import {bindConversation} from "./conversation.mjs";
import {createActivityReader} from "../website/assets/activity-reader.mjs";
import {bindActivityReader} from "../website/assets/activity-reader-render.mjs";
try{
  // This candidate is intentionally outside the public deploy root.
  // A trusted operator must serve it on an authorized private HTTPS origin.
  if(location.protocol!=="https:"||!globalThis.isSecureContext)
    throw new Error("HTTPS required");
  const nodes=Object.fromEntries(Object.entries({
    token:"token",signIn:"sign-in",signOut:"sign-out",question:"question",count:"count",
    submit:"submit",read:"read",next:"next",status:"status",answer:"answer"
  }).map(([key,id])=>[key,document.getElementById("beta-"+id)]));
  if(Object.values(nodes).some(node=>!node))throw new Error("Missing controls");
  const mailbox=createBetaMailbox({enabled:true,fetcher:(path,opts)=>fetch(path,opts),
    uuid:()=>crypto.randomUUID(),clock:()=>Date.now()});
  const view=bindConversation(nodes,mailbox);
  // Browser back/forward cache must never restore a credential or reply.
  window.addEventListener("pagehide",()=>view.close());
  // Only the private HTTPS beta wires the reader. No network polling.
  const activityNodes={label:document.getElementById("beta-activity-label"),
    stamp:document.getElementById("beta-activity-stamp"),
    refresh:document.getElementById("beta-activity-refresh")};
  if(Object.values(activityNodes).every(Boolean)){
    const reader=createActivityReader({enabled:true,fetcher:(path,opts)=>fetch(path,opts),clock:()=>Date.now()});
    const activity=bindActivityReader(activityNodes,reader);
    let timer=null;
    function tick(){
      clearTimeout(timer);
      if(document.visibilityState==="hidden")return;
      activity.render();
      // Local expiry/refresh-button rendering only; never a network request.
      timer=setTimeout(tick,1000);
    }
    document.addEventListener("visibilitychange",tick);
    window.addEventListener("pagehide",()=>{clearTimeout(timer);activity.close();});
    tick();
  }
}catch{
  console.error("Private beta initialization refused.");
  const status=document.getElementById("beta-status");
  if(status)status.textContent="Private beta unavailable. Authorized HTTPS host required; nothing was sent.";
}
