import {validText,terminal} from "./beta-mailbox-state.mjs";

const STATUS=Object.freeze({
  idle:"Credential loaded locally; server authorization is not yet verified.",
  draft:"Question retained. Send the same draft when the request interval allows.",
  uncertain:"Delivery is unconfirmed. Retry this exact question; do not create a duplicate.",
  accepted:"Question accepted by the mailbox. Check for a reply later.",
  submitted:"Question is waiting in the mailbox.",
  claimed:"Question has been claimed by the bridge.",
  locally_accepted:"Question admitted locally; no approved answer yet.",
  answered:"Reviewed reply received.",
  rejected:"Question rejected. No reply available.",
  expired:"Question expired. No reply available.",
  not_found:"Question unavailable to this credential. No reply displayed.",
  unavailable:"Reply status unavailable. Check again later.",
  unauthorized:"Credential rejected or expired. Ask the operator for assistance before clearing the session.",
  denied:"Request refused.",
  invalid:"Request invalid.",
  conflict:"Request conflicts with existing mailbox state; seek operator assistance.",
  member_busy:"A question is already outstanding.",
  rate_limited:"Rate limit reached. Wait before retrying this request.",
  member_quota:"Member quota reached.",
  community_quota:"Community quota reached.",
  paused:"Mailbox admission is paused.",
  full:"Mailbox is at capacity."
});
export function bindConversation(nodes,mailbox){
  const {token,signIn,signOut,question,count,submit,read,next,status,answer}=nodes;
  let notice=null,closed=false;
  function render(){
    const s=mailbox.snapshot();
    token.disabled=closed||s.signedIn||s.busy;
    signIn.disabled=closed||s.signedIn||s.busy||!token.value.trim();
    signOut.disabled=closed||!s.signedIn;
    question.disabled=closed||!s.signedIn||s.busy||s.hasDraft;
    count.textContent=Array.from(question.value).length+" / 2000";
    submit.disabled=closed||!s.signedIn||s.busy||!!s.id||terminal(s.status)||!validText(question.value,2000);
    submit.textContent=s.hasDraft?"Retry same question":"Send question";
    read.disabled=closed||!s.signedIn||s.busy||!s.id||terminal(s.status);
    next.disabled=closed||!s.signedIn||s.busy||!terminal(s.status);
    // Reply is rendered as inert text, never interpreted markup.
    answer.textContent=s.signedIn&&s.status==="answered"&&typeof s.text==="string"?s.text:"No confirmed reply.";
    status.textContent=notice??(closed?"Private beta closed. Reload to begin another session.":
      !s.signedIn?"Load an operator-issued credential. Nothing has been sent.":
      s.busy?"Request in progress; no result confirmed yet.":STATUS[s.status]??"Status unavailable.");
    return s;
  }
  function clear(close=false){
    mailbox.signOut();
    token.value="";question.value="";notice=null;closed=close;
    render();
  }
  function reportError(){
    console.error("Private conversation action unavailable.");
    notice="Action unavailable. No new result confirmed.";
    render();
  }
  token.addEventListener("input",()=>{notice=null;render();});
  question.addEventListener("input",()=>{notice=null;render();});
  signIn.addEventListener("click",()=>{
    try{
      if(closed)return;
      const ok=mailbox.signIn(token.value.trim());token.value="";
      notice=ok?null:"Credential format refused. No request sent.";render();
    }catch{reportError();}
  });
  signOut.addEventListener("click",()=>{try{clear();}catch{reportError();}});
  async function request(op){
    try{
      if(closed)return;
      notice=null;
      const result=op==="submit"?mailbox.submit(question.value):mailbox.read();
      render();await result;render();
    }catch{reportError();}
  }
  submit.addEventListener("click",()=>request("submit"));
  read.addEventListener("click",()=>request("read"));
  next.addEventListener("click",()=>{
    try{if(!closed&&mailbox.next()){question.value="";notice=null;}render();}
    catch{reportError();}
  });
  render();
  return Object.freeze({render,close:()=>clear(true)});
}
