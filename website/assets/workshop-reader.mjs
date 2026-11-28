// Explicit same-origin read only. No background network, storage or credentials.
import {parseWorkshop} from "./workshop-state.mjs";
const PATH="/api/v1/workshop",INTERVAL=60000,MAX_BYTES=1024;

export function createWorkshopReader({enabled=false,fetcher,clock}={}){
  if(enabled!==true||typeof fetcher!=="function"||typeof clock!=="function")
    throw Error("Workshop reader disabled");
  let raw=null,highWater=null,lastRequest=-Infinity,notBefore=0;
  let busy=false,closed=false,controller=null;
  function snapshot(){
    const now=clock(),state=parseWorkshop(raw,Math.floor(now/1000));
    if(state.status!=="reviewed")raw=null;
    return Object.freeze({state,busy,closed,canRefresh:!closed&&!busy
      &&Number.isSafeInteger(now)&&now>=0&&now>=lastRequest+INTERVAL&&now>=notBefore,
      refreshAt:Math.max(lastRequest+INTERVAL,notBefore)});
  }
  async function read(){
    if(!snapshot().canRefresh)return;
    lastRequest=clock();busy=true;controller=new AbortController();
    const signal=controller.signal,timeout=setTimeout(()=>controller?.abort(),5000);
    try{
      const response=await fetcher(PATH,{method:"GET",credentials:"omit",cache:"no-store",
        redirect:"error",referrerPolicy:"no-referrer",headers:{Accept:"application/json"},signal});
      if(closed||signal.aborted)return;
      const retry=response.headers.get("retry-after");
      if(retry!==null&&/^\d{1,6}$/.test(retry))
        notBefore=Math.max(notBefore,clock()+Math.min(Number(retry),86400)*1000);
      if(response.status!==200||!/^application\/json(?:;|$)/i.test(response.headers.get("content-type")??"")
          ||!response.body){
        raw=null;if(response.body)void response.body.cancel().catch(()=>{});return;
      }
      const stream=response.body.getReader(),decoder=new TextDecoder("utf-8",{fatal:true});
      let text="",size=0;
      try{
        while(true){
          const {done,value}=await stream.read();
          if(done)break;
          size+=value.byteLength;
          if(size>MAX_BYTES){void stream.cancel().catch(()=>{});throw Error("oversized Workshop response");}
          text+=decoder.decode(value,{stream:true});
        }
        text+=decoder.decode();
      }finally{stream.releaseLock();}
      const now=Math.floor(clock()/1000),state=parseWorkshop(text,now);
      if(closed||signal.aborted)return;
      if(state.status!=="reviewed"||state.expiresAt>now+120||
          (highWater&&(state.generatedAt<highWater.generatedAt||
            (state.generatedAt===highWater.generatedAt&&state.stage!==highWater.stage)))){
        raw=null;return;
      }
      highWater=state;raw=text;
    }catch{
      raw=null;console.warn("Workshop observation unavailable.");
    }finally{
      clearTimeout(timeout);controller=null;busy=false;
      if(closed||signal.aborted)raw=null;
    }
  }
  function close(){closed=true;raw=null;highWater=null;controller?.abort();}
  return Object.freeze({snapshot,read,close});
}
