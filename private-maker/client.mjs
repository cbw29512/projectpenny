// Separate admin session in memory; never accepts browser-supplied MFA or roles.
const ROOT="/api/v1/admin/";
const exact=(v,keys)=>v!==null&&typeof v==="object"&&!Array.isArray(v)
  &&Object.keys(v).length===keys.length&&keys.every(k=>Object.hasOwn(v,k));
const validStatus=v=>exact(v,["admissionOpen","pending","processing"])
  &&typeof v.admissionOpen==="boolean"&&[v.pending,v.processing].every(n=>Number.isSafeInteger(n)&&n>=0&&n<=512);
export function createMakerClient({enabled=false,fetcher,clock}={}){
  if(enabled!==true||typeof fetcher!=="function"||typeof clock!=="function")throw Error("Admin unavailable");
  let credential=null,busy=false,closed=false,current=null,notice="signed_out";
  let last=-Infinity,notBefore=0,epoch=0,controller=null,uncertain=false;
  function signIn(value){
    if(closed||busy||credential||typeof value!=="string"||value.length>8185||! /^[!-~]+$/.test(value))return false;
    credential=value;notice="credential_loaded";return true;
  }
  function signOut(){
    epoch++;controller?.abort();credential=null;current=null;notice="signed_out";
    // Preserve local request cooldown, even across sign-out.
  }
  function snapshot(){
    const now=clock();
    const fresh=current&&Number.isSafeInteger(now)&&now>=current.at&&now-current.at<60000;
    const ready=!closed&&!!credential&&!busy&&Number.isSafeInteger(now)&&now>=0&&now>=last+5000&&now>=notBefore;
    return Object.freeze({signedIn:!!credential,busy,closed,status:fresh?current.value:null,
      notice,uncertain,canRead:ready,canPause:ready&&!uncertain&&!!fresh&&current.value.admissionOpen});
  }
  async function request(op,confirmation){
    const view=snapshot(),pause=op==="pause";
    if(pause?(!view.canPause||confirmation!=="PAUSE ADMISSION"):!view.canRead)return;
    const generation=epoch;
    last=clock();busy=true;notice="request_pending";
    controller=new AbortController();
    const signal=controller.signal;
    const timeout=setTimeout(()=>controller?.abort(),5000);
    // A pause could commit before a response is lost. Require status reconciliation.
    if(pause){uncertain=true;current=null;}
    try{
      const response=await fetcher(ROOT+(pause?"pause-admission":"status"),{
        method:pause?"POST":"GET",headers:{Authorization:"Bearer "+credential,Accept:"application/json",
          ...(pause?{"Content-Type":"application/json"}:{})},
        ...(pause?{body:JSON.stringify({confirm:confirmation})}:{}),
        credentials:"omit",cache:"no-store",redirect:"error",referrerPolicy:"no-referrer",signal});
      if(generation!==epoch||closed||signal.aborted)return;
      const retry=response.headers.get("retry-after");
      if(retry&&/^\d{1,6}$/.test(retry))notBefore=Math.max(notBefore,clock()+Math.min(Number(retry),86400)*1000);
      if(response.status!==200||!/^application\/json(?:;|$)/i.test(response.headers.get("content-type")??"")||!response.body){
        if(response.body)void response.body.cancel().catch(()=>{});
        current=null;notice=response.status===401?"unauthorized":response.status===429?"rate_limited":"unavailable";
        return;
      }
      const reader=response.body.getReader(),decoder=new TextDecoder("utf-8",{fatal:true});
      let text="",size=0;
      try{
        while(true){
          const {done,value}=await reader.read();if(done)break;
          size+=value.byteLength;
          if(size>1024){void reader.cancel().catch(()=>{});throw Error("Oversized admin response");}
          text+=decoder.decode(value,{stream:true});
        }
        text+=decoder.decode();
      }finally{reader.releaseLock();}
      const data=JSON.parse(text);
      if(generation!==epoch||closed||signal.aborted)return;
      if(pause){
        if(!exact(data,["status"])||data.status!=="admission_closed")throw Error("Invalid pause receipt");
        uncertain=false;notice="pause_confirmed";
      }else{
        if(!validStatus(data))throw Error("Invalid admin status");
        current={value:Object.freeze({...data}),at:clock()};uncertain=false;notice="status_confirmed";
      }
    }catch{
      if(generation===epoch){current=null;notice="unavailable";}
      console.warn("Maker request unavailable.");
    }finally{
      clearTimeout(timeout);controller=null;busy=false;
      if(generation===epoch&&signal.aborted){current=null;notice="unavailable";}
    }
  }
  return Object.freeze({signIn,signOut,snapshot,read:()=>request("read"),
    pause:confirmation=>request("pause",confirmation),close:()=>{closed=true;signOut();}});
}
