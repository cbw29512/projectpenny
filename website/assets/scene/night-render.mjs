import { PAJAMAS,pajamasFor } from "./office-pajamas.mjs";
import { parseRest,nightView } from "./night-state.mjs";
const ART=new Map(PAJAMAS.map(p=>[p.id,"/assets/scene/pajamas/"+p.id+".svg"]));

const DREAMS=Object.freeze(["Negotiating with a toaster.","A castle made of graphics cards.","Counting electric sheep.","A coffee mug that refills itself.","A spaceship powered by spare RAM.","An infinite library of debugging books.","A garden of tiny robot flowers."]);

export function nightPresenter(scene,art,notice,link,dream){
  let hadReviewed=false,latest=-1;
  function clear(message){
    art.hidden=true;delete scene.dataset.nightMode;
    if(dream){dream.hidden=true;dream.textContent="";}
    notice.textContent=message;link.textContent="Browse pajamas";link.href="#collection-pajamas";
  }
  function show(p,mode,message){
    if(!ART.has(p.id))return false;
    art.src=ART.get(p.id);art.hidden=false;
    scene.dataset.nightMode=mode;
    if(dream){
      // Fixed fictional entertainment; never a model request or an activity record.
      dream.hidden=false;
      dream.textContent="Fictional dream — "+DREAMS[PAJAMAS.indexOf(p)];
    }
    notice.textContent=message;
    link.textContent=p.phrase;link.href="#design-"+p.id;
    return true;
  }
  return {
    review(text,now){
      try{
        const s=parseRest(text,now);
        if(!s||s.sampledAt<latest){
          if(hadReviewed)clear("Rest status unavailable — no current sleep claim.");
          return false;
        }
        hadReviewed=true;latest=s.sampledAt;
        const view=nightView(s,now);
        if(view){
          return show(view.pajamas,"reviewed","ZZZZZ");
        }
        clear(s.state==="draining"?"Rest transition pending — finishing work.":s.state==="blocked"?"Rest blocked — recovery required.":"Reviewed awake state.");
        return true;
      }catch{console.error("Night state unavailable.");clear("Rest state unavailable.");return false;}
    },
    preview(date){
      try{
        if(hadReviewed)return false;
        const p=pajamasFor(date);
        return p?show(p,"preview","Nighttime artwork preview only — not actual rest or work status."):false;
      }catch{console.error("Night preview unavailable.");return false;}
    },
    day(){
      if(hadReviewed)return false;
      clear("Daytime preview — no verified rest state connected.");return true;
    }
  };
}
function boot(){
  const get=id=>document.getElementById(id);
  const scene=get("penny-scene"),art=get("night-pajama-art"),notice=get("night-status"),link=get("night-pajama-link"),source=get("rest-snapshot");
  const date=get("daily-office-date"),night=get("night-preview"),day=get("night-preview-day");
  if(!scene||!art||!notice||!link||!source||!date||!night||!day)return;
  const view=nightPresenter(scene,art,notice,link,get("penny-dream"));
  let timer;
  const refresh=()=>{
    clearTimeout(timer);
    if(document.visibilityState==="hidden")return;
    if(view.review(source.textContent,Math.floor(Date.now()/1000))){night.disabled=true;day.disabled=true;}
    timer=setTimeout(refresh,5000);
  };
  night.addEventListener("click",()=>{if(!view.preview(date.value)&&!night.disabled)notice.textContent="Choose a valid preview date first.";});
  day.addEventListener("click",()=>view.day());
  link.addEventListener("click",()=>{const target=get(link.hash.slice(1));if(target?.tagName==="DETAILS")target.open=true;});
  window.addEventListener("pageshow",refresh);
  window.addEventListener("pagehide",()=>clearTimeout(timer));
  document.addEventListener("visibilitychange",refresh);
  refresh();
}
try{if(typeof document!=="undefined")boot();}
catch{console.error("Night renderer initialization failed.");}
