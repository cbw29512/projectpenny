// Explicit invitation-only home integration. No query-string opt-in.
import {createBetaMailbox} from "./beta-mailbox.mjs";
import {bindConversation} from "./conversation.mjs";
const ORIGIN="https://projectpenny.netlify.app";
export function bindHomeConversation({document,window,fetcher,uuid,clock,origin,secure}){
  const get=id=>document.getElementById(id);
  const root=get("home-conversation");
  if(root?.dataset.live!=="true")return null;
  // Never fall back to preview if an attempted live setup is invalid.
  if(origin!==ORIGIN||secure!==true)throw Error("approved HTTPS beta origin required");
  const nodes=Object.fromEntries(Object.entries({
    token:"home-beta-token",signIn:"home-beta-sign-in",signOut:"home-beta-sign-out",
    question:"question",count:"count",submit:"home-beta-submit",read:"home-beta-read",
    next:"home-beta-next",status:"notice",answer:"welcome"
  }).map(([key,id])=>[key,get(id)]));
  const auth=get("home-beta-auth"),actions=get("home-beta-actions"),preview=get("preview-send"),
    label=get("speech-label");
  if(Object.values(nodes).some(n=>!n)||!auth||!actions||!preview||!label)
    throw Error("missing private beta controls");
  const mailbox=createBetaMailbox({enabled:true,fetcher,uuid,clock});
  const view=bindConversation(nodes,mailbox);
  auth.hidden=false;actions.hidden=false;preview.hidden=true;preview.disabled=true;
  label.textContent="PENNY SAYS · REVIEWED PRIVATE REPLY";
  window.addEventListener("pagehide",()=>view.close());
  return view;
}
