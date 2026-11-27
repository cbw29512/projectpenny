const COPY=Object.freeze({signed_out:"Load a provider-issued administrator credential.",
 credential_loaded:"Credential loaded locally; server authorization not yet verified.",
 request_pending:"Request pending; no outcome confirmed.",status_confirmed:"Cloud mailbox status verified.",
 pause_confirmed:"Cloud admission closed. Existing work may continue. Refresh status to verify.",
 unauthorized:"Administrator session refused or expired. Recent MFA is required.",
 rate_limited:"Request rate limited; wait before checking again.",unavailable:"No result confirmed."});
export function bindMaker(nodes,client){
  const {token,load,clear,read,confirm,pause,admission,pending,processing,notice}=nodes;
  function render(){
    const s=client.snapshot();
    token.disabled=s.closed||s.signedIn||s.busy;load.disabled=token.disabled||!token.value;
    clear.disabled=s.closed||!s.signedIn;
    read.disabled=!s.canRead;confirm.disabled=!s.canPause;
    pause.disabled=!s.canPause||confirm.value!=="PAUSE ADMISSION";
    admission.textContent=s.status?(s.status.admissionOpen?"Open":"Closed"):"Unknown";
    pending.textContent=s.status?String(s.status.pending):"—";
    processing.textContent=s.status?String(s.status.processing):"—";
    notice.textContent=s.closed?"Console closed.":(COPY[s.notice]??"Unavailable.")+
      (s.uncertain?" Previous pause outcome uncertain; check status before another attempt.":"");
  }
  async function perform(action){
    try{const task=action();render();await task;render();}
    catch{console.error("Maker console action failed.");client.signOut();render();}
  }
  token.addEventListener("input",render);confirm.addEventListener("input",render);
  load.addEventListener("click",()=>{try{client.signIn(token.value);token.value="";render();}
    catch{client.signOut();render();}});
  clear.addEventListener("click",()=>{client.signOut();token.value="";confirm.value="";render();});
  read.addEventListener("click",()=>perform(()=>client.read()));
  pause.addEventListener("click",()=>perform(()=>{const value=confirm.value;confirm.value="";return client.pause(value);}));
  render();
  return Object.freeze({render,close:()=>{client.close();token.value="";confirm.value="";render();}});
}
