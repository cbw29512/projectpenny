// Fixed, versioned motivational poster concepts, not approved physical stock.
export const POSTERS = Object.freeze([
  {id:"poster-persistence-v1",theme:"persistence",title:"PERSISTENCE",lines:["Failure is just","a feature request."],symbol:"↗"},
  {id:"poster-dream-big-v1",theme:"dream-big",title:"DREAM BIG",lines:["Start with","available RAM."],symbol:"✦"},
  {id:"poster-progress-v1",theme:"progress",title:"PROGRESS",lines:["One commit","at a time."],symbol:"✓"},
  {id:"poster-optimism-v1",theme:"optimism",title:"OPTIMISM",lines:["Everything is","debuggable."],symbol:"☀"},
  {id:"poster-ambition-v1",theme:"ambition",title:"AMBITION",lines:["Small budget.","Massive plans."],symbol:"↑"},
  {id:"poster-mission-v1",theme:"mission",title:"THE MISSION",lines:["$0 to","$1,000,000"],symbol:"$"}
].map(p => Object.freeze({...p,lines:Object.freeze(p.lines),phrase:p.lines.join(" ")})));
