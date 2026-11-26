// Seven fixed nighttime designs. No runtime artwork generation.
export const PAJAMAS=Object.freeze([
  {id:"pajamas-sleep-mode-v1",name:"Sleep Mode",lines:["SLEEP","MODE"]},
  {id:"pajamas-do-not-disturb-v1",name:"Do Not Disturb",lines:["DO NOT","DISTURB"]},
  {id:"pajamas-hibernating-v1",name:"System Hibernating",lines:["SYSTEM","HIBERNATING"]},
  {id:"pajamas-recharging-v1",name:"Recharging Ambition",lines:["RECHARGING","AMBITION"]},
  {id:"pajamas-binary-v1",name:"Dreaming in Binary",lines:["DREAMING","IN BINARY"]},
  {id:"pajamas-good-night-v1",name:"Good Night World",lines:["GOOD NIGHT","WORLD!"]},
  {id:"pajamas-ctrl-alt-sleep-v1",name:"Ctrl Alt Sleep",lines:["CTRL + ALT","+ SLEEP"]}
].map(p=>Object.freeze({...p,lines:Object.freeze(p.lines),phrase:p.lines.join(" ")})));
export function pajamasFor(date){
  try{
    if(typeof date!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(date)||date<"2000-01-01"||date>"2099-12-31")return null;
    const stamp=Date.parse(date+"T00:00:00Z");
    if(!Number.isFinite(stamp)||new Date(stamp).toISOString().slice(0,10)!==date)return null;
    // Monday through Sunday; civil date only, no device timezone.
    return PAJAMAS[(new Date(stamp).getUTCDay()+6)%7];
  }catch{console.error("Pajama selection unavailable.");return null;}
}
