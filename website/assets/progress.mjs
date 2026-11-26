import {parseProgress,metricText} from "./progress-state.mjs";

function boot() {
  const source=document.getElementById("progress-snapshot");
  const status=document.getElementById("snapshot-status");
  const updated=document.getElementById("snapshot-updated");
  if (!source || !status || !updated) return;
  const cells=[...document.querySelectorAll("[data-progress-scope][data-progress-key]")];
  let timer;
  const render=()=>{
    clearTimeout(timer);
    const now=Math.floor(Date.now()/1000);
    const state=parseProgress(source.textContent,now);
    for (const cell of cells) {
      cell.textContent=metricText(state,cell.dataset.progressScope,cell.dataset.progressKey);
    }
    status.textContent=state.status==="reviewed"?"Reviewed historical snapshot":
      state.status==="stale"?"Snapshot expired — figures hidden":"No reviewed snapshot available";
    updated.textContent=state.generatedAt===null?"No verified update timestamp":
      "Snapshot generated: "+new Date(state.generatedAt*1000).toISOString();
    if (state.status==="reviewed") {
      // Local expiry only. No polling, fetch, inference, or background network.
      timer=setTimeout(render,Math.max(1,state.expiresAt*1000-Date.now()));
    }
  };
  render();
  window.addEventListener("pageshow",render);
  document.addEventListener("visibilitychange",()=>{
    if (document.visibilityState==="visible") render();
  });
}
try { boot(); }
catch { console.error("Penny progress initialization failed."); }
