import {observationView} from "./activity-observation.mjs";
const PATH="/api/v1/activity";
const INTERVAL=60000;
const MAX_BYTES=512;

// Explicit opt-in only. No auto-fetch, credentials, storage or inference.
export function createActivityReader({enabled=false,fetcher,clock}={}){
  if(enabled!==true||typeof fetcher!=="function"||typeof clock!=="function")
    throw Error("Activity reader disabled");
  let current=null,highWater=null,lastRequest=-Infinity,notBefore=0;
  let busy=false,closed=false,controller=null;
  function snapshot(){
    const now=clock();
    const view=observationView(current,Math.floor(now/1000));
    if(!view)current=null;
    return Object.freeze({view,busy,closed,
      canRefresh:!closed&&!busy&&Number.isSafeInteger(now)&&now>=0
        &&now>=lastRequest+INTERVAL&&now>=notBefore});
  }
  async function read(){
    if(!snapshot().canRefresh)return snapshot();
    lastRequest=clock();busy=true;
    controller=new AbortController();
    const signal=controller.signal;
    const timeout=setTimeout(()=>controller?.abort(),5000);
    try{
      const response=await fetcher(PATH,{method:"GET",credentials:"omit",
        cache:"no-store",redirect:"error",referrerPolicy:"no-referrer",
        headers:{Accept:"application/json"},signal});
      if(closed||signal.aborted)return;
      const retry=response.headers.get("retry-after");
      if(retry!==null&&/^\d{1,6}$/.test(retry)){
        notBefore=Math.max(notBefore,clock()+Math.min(Number(retry),86400)*1000);
      }
      if(response.status!==200||!/^application\/json(?:;|$)/i.test(response.headers.get("content-type")??"")
          ||!response.body){
        current=null;
        if(response.body)void response.body.cancel().catch(()=>{});
        return;
      }
      const reader=response.body.getReader(),decoder=new TextDecoder("utf-8",{fatal:true});
      let text="",size=0;
      try{
        while(true){
          const {done,value}=await reader.read();
          if(done)break;
          size+=value.byteLength;
          if(size>MAX_BYTES){void reader.cancel().catch(()=>{});throw Error("Oversized activity response");}
          text+=decoder.decode(value,{stream:true});
        }
        text+=decoder.decode();
      }finally{reader.releaseLock();}
      const value=JSON.parse(text),view=observationView(value,Math.floor(clock()/1000));
      if(closed||signal.aborted)return;
      if(!view||(highWater&&(view.sampledAt<highWater.sampledAt||
           (view.sampledAt===highWater.sampledAt&&view.label!==highWater.label)))){
        current=null;return;
      }
      highWater=view;current=value;
    }catch{
      current=null;console.warn("Activity observation unavailable.");
    }finally{
      clearTimeout(timeout);controller=null;busy=false;
      if(closed||signal.aborted)current=null;
    }
  }
  function close(){
    closed=true;current=null;highWater=null;controller?.abort();
  }
  return Object.freeze({snapshot,read,close});
}
