import { skyAt, easternClock } from "./office-sky.mjs";

const COLORS=Object.freeze({
  day:["#79b9d7","#b5d4d8","#759d7e"],
  dawn:["#b991a5","#f6c398","#747d85"],
  dusk:["#a06e91","#e9a379","#695b80"],
  twilight:["#30486d","#8c83a0","#3c5266"],
  night:["#14233f","#263954","#334b54"]
});
const STARS=Object.freeze([[9,9],[25,22],[42,7],[58,17],[77,8],[94,25],[66,35]]);
function disk(ctx,x,y,r,color) {
  ctx.fillStyle=color;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();
}
function position(body) {
  // Schematic sky projection, not a surveyed view through a compass-aligned window.
  return [Math.max(9,Math.min(94,51.5+body.hourAngle/2.7)),
    Math.max(9,Math.min(58,56-body.alt*0.53))];
}
function moonDisk(ctx,x,y,sky) {
  const r=7;
  disk(ctx,x,y,r,"#35435b");
  const right=sky.phaseAngle<180;
  const c=1-2*sky.illumination;
  // Join outer limb and elliptical terminator; handles crescent and gibbous.
  ctx.beginPath();
  for(let n=0;n<=40;n++){
    const dy=-r+2*r*n/40,edge=Math.sqrt(Math.max(0,r*r-dy*dy));
    const px=x+(right?edge:-edge);
    if(n===0)ctx.moveTo(px,y+dy);else ctx.lineTo(px,y+dy);
  }
  for(let n=40;n>=0;n--){
    const dy=-r+2*r*n/40,edge=Math.sqrt(Math.max(0,r*r-dy*dy));
    ctx.lineTo(x+(right?c:-c)*edge,y+dy);
  }
  ctx.closePath();ctx.fillStyle="#eee8d1";ctx.fill();
}
export function drawSky(ctx,sky) {
  const [top,bottom,ground]=COLORS[sky.period];
  const gradient=ctx.createLinearGradient(0,0,0,76);
  gradient.addColorStop(0,top);gradient.addColorStop(1,bottom);
  ctx.fillStyle=gradient;ctx.fillRect(0,0,103,76);
  if(sky.period==="night"||sky.period==="twilight"){
    for(const [x,y] of STARS)disk(ctx,x,y,0.65,"#e4e5d9");
  }
  if(sky.sunVisible)disk(ctx,...position(sky.sun),8,"#ffe8a3");
  if(sky.moonVisible)moonDisk(ctx,...position(sky.moon),sky);
  // Keep the familiar landscape silhouette and mullions inside the old pane.
  ctx.fillStyle=ground;ctx.beginPath();ctx.moveTo(0,75);
  for(const [x,y] of [[29,51],[47,67],[76,33],[103,58],[103,76],[0,76]])
    ctx.lineTo(x,y);
  ctx.closePath();ctx.fill();
  ctx.fillStyle="#263f50";ctx.fillRect(48.5,0,5,76);ctx.fillRect(0,35.5,103,5);
}
function boot() {
  const canvas=document.getElementById("office-sky"),caption=document.getElementById("office-sky-caption");
  if(!canvas||!caption)return;
  const ctx=canvas.getContext("2d");
  if(!ctx)return;
  ctx.scale(4,4);
  let timer;
  const update=()=>{
    clearTimeout(timer);
    if(document.visibilityState==="hidden")return;
    try {
      // Local device clock is acceptable for scenery only, never for reviewed
      // daily design, work, payment, rest or financial authority.
      const now=Date.now(),sky=skyAt(now),clock=easternClock(now);
      if(!sky||!clock)throw new Error("unavailable clock");
      drawSky(ctx,sky);canvas.hidden=false;
      caption.textContent=clock+" · "+sky.period+" · "+sky.phase
        +" ("+Math.round(sky.illumination*100)+"% lit) · "
        +(sky.moonVisible?"Moon above horizon":"Moon not displayed")
        +" · calculated scenery, device clock";
      timer=setTimeout(update,60000-now%60000);
    }catch{
      console.error("Penny window render unavailable.");
      canvas.hidden=true;caption.textContent="Calculated sky unavailable.";
    }
  };
  window.addEventListener("pageshow",update);
  window.addEventListener("pagehide",()=>clearTimeout(timer));
  document.addEventListener("visibilitychange",update);
  update();
}
try { if(typeof document!=="undefined")boot(); }
catch { console.error("Penny window initialization failed."); }
