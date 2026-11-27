import {isId,validText,decodeReceipt,decodeRead,terminal} from "./beta-mailbox-state.mjs";
const MAX_BYTES=100000;
const PATH="/api/v1/questions";
const TOKEN=/^v1\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/;
const MIN_INTERVAL=15000;

// Not wired into the public homepage. Trusted beta adapter explicitly opts in.
// No storage, automatic retry, polling timer, URL tokens or cross-origin requests.
export function createBetaMailbox({enabled=false,fetcher,uuid,clock}={}){
  if(enabled!==true||typeof fetcher!=="function"||typeof uuid!=="function"||typeof clock!=="function")
    throw new Error("Private beta unavailable");
  let token=null,pending=null,busy=false,lastRequest=-Infinity,notBefore=0,generation=0,controller=null;
  function clear(){
    generation++;controller?.abort();token=null;pending=null;lastRequest=-Infinity;notBefore=0;
  }
  function signIn(value){
    if(busy||pending||typeof value!=="string"||value.length>1017||!TOKEN.test(value))return false;
    clear();token=value;return true;
  }
  function snapshot(){
    return Object.freeze({signedIn:token!==null,busy,hasDraft:pending!==null,
      id:pending?.id??null,status:pending?.status??"idle",text:pending?.answer??null});
  }
  async function exchange(path,method,body){
    const now=clock();
    if(!Number.isSafeInteger(now)||now<0||now<lastRequest+MIN_INTERVAL||now<notBefore)
      return {limited:true};
    lastRequest=now;
    controller=new AbortController();
    const signal=controller.signal;
    const timer=setTimeout(()=>controller?.abort(),10000);
    try{
      const response=await fetcher(path,{method,headers:{Authorization:"Bearer "+token,
        ...(body?{"Content-Type":"application/json"}:{})},...(body?{body:JSON.stringify(body)}:{}),
        credentials:"omit",cache:"no-store",redirect:"error",referrerPolicy:"no-referrer",signal});
      const retry=response.headers.get("retry-after");
      if(retry!==null&&/^\d{1,5}$/.test(retry))
        notBefore=Math.max(notBefore,now+Math.min(Number(retry),86400)*1000);
      if(!/^application\/json(?:;|$)/i.test(response.headers.get("content-type")??"")
        ||!response.body)return null;
      const reader=response.body.getReader(),decoder=new TextDecoder("utf-8",{fatal:true});
      let size=0,text="";
      try{
        while(true){
          const {done,value}=await reader.read();
          if(done)break;
          size+=value.byteLength;
          if(size>MAX_BYTES){await reader.cancel();return null;}
          text+=decoder.decode(value,{stream:true});
        }
        text+=decoder.decode();
        return {code:response.status,data:JSON.parse(text)};
      }finally{reader.releaseLock();}
    }catch{console.warn("Private mailbox request unavailable.");return null;}
    finally{clearTimeout(timer);controller=null;}
  }
  async function submit(text){
    if(!token||busy||!validText(text,2000))return snapshot();
    // A lost response is retried ONLY with the original key and exact draft.
    if(pending&&(pending.id||pending.draft!==text||terminal(pending.status)))return snapshot();
    if(!pending){
      const key=uuid();
      if(!isId(key))return snapshot();
      pending={key,draft:text,id:null,status:"draft",answer:null};
    }
    busy=true;const epoch=generation;
    try{
      const result=await exchange(PATH,"POST",{key:pending.key,text:pending.draft});
      if(epoch!==generation)return snapshot();
      if(result?.limited)return snapshot();
      const receipt=result?decodeReceipt(result.code,result.data):{status:"uncertain"};
      pending.status=receipt.status;
      if(receipt.status==="accepted"){pending.id=receipt.id;pending.draft=null;}
    }catch{if(epoch===generation)pending.status="uncertain";}
    finally{busy=false;}
    return snapshot();
  }
  async function read(){
    if(!token||busy||!pending?.id||terminal(pending.status))return snapshot();
    busy=true;const epoch=generation;
    try{
      const result=await exchange(PATH+"/"+pending.id,"GET");
      if(epoch!==generation||result?.limited)return snapshot();
      const reply=result?decodeRead(result.code,result.data,pending.id):{status:"unavailable"};
      pending.status=reply.status;
      pending.answer=reply.status==="answered"?reply.text:null;
    }catch{if(epoch===generation)pending.status="unavailable";}
    finally{busy=false;}
    return snapshot();
  }
  // Explicit discard only after terminal state; never silently replace an
  // ambiguous request. Sign-out always erases all local state.
  function next(){
    if(busy||!pending||!terminal(pending.status))return false;
    pending=null;return true;
  }
  return Object.freeze({signIn,signOut:clear,snapshot,submit,read,next});
}
