// Historical observations never drive the scene, chat status or sleep state.
export function bindActivityReader({label,stamp,refresh},reader){
  function render(){
    const s=reader.snapshot();
    label.textContent=s.closed?"Activity reader closed.":s.view?.label??"No recent activity observation.";
    stamp.textContent=s.view?new Date(s.view.sampledAt*1000).toISOString():"";
    refresh.disabled=!s.canRefresh;
    refresh.textContent=s.busy?"Checking activity…":"Check activity";
  }
  refresh.addEventListener("click",async()=>{
    try{
      const pending=reader.read();render();await pending;render();
    }catch{
      console.error("Activity display unavailable.");
      reader.close();render();
    }
  });
  render();
  return Object.freeze({render,close:()=>{reader.close();render();}});
}
