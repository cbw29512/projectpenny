import {parseTimeline,filterEvents} from "./timeline-state.mjs";

function boot() {
  const source=document.getElementById("timeline-snapshot");
  const list=document.getElementById("timeline-events");
  const status=document.getElementById("timeline-status");
  const filter=document.getElementById("timeline-filter");
  if (!source||!list||!status||!filter) return;
  let timer;
  const render=()=>{
    clearTimeout(timer);
    const state=parseTimeline(source.textContent,Math.floor(Date.now()/1000));
    const events=filterEvents(state,filter.value);
    list.replaceChildren();
    filter.disabled=state.status!=="reviewed";
    if (state.status==="reviewed") {
      for (const event of events) {
        const item=document.createElement("li");
        const date=document.createElement("time");
        date.dateTime=event.date;
        date.textContent=event.date+" (UTC)";
        const label=document.createElement("p");
        label.textContent=event.label;
        item.append(date,label);
        list.append(item);
      }
      status.textContent=events.length?
        "Showing "+events.length+" of "+state.events.length+" reviewed recent events.":
        "No reviewed events match this filter.";
      timer=setTimeout(render,Math.max(1,state.expiresAt*1000-Date.now()));
    } else {
      status.textContent=state.status==="stale"?
        "Timeline snapshot expired — events hidden.":"No reviewed timeline available.";
    }
  };
  filter.addEventListener("change",render);
  window.addEventListener("pageshow",render);
  document.addEventListener("visibilitychange",()=>{
    if(document.visibilityState==="visible") render();
  });
  render();
}
try { boot(); }
catch { console.error("Penny timeline initialization failed."); }
