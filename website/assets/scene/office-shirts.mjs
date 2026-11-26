// Versioned slogan designs. Older color-only IDs are not silently repurposed.
export const SHIRTS = Object.freeze([
  {id:"shirt-teal-slogan-v1",color:"teal",name:"Teal",lines:["HELLO,","WORLD!"]},
  {id:"shirt-plum-slogan-v1",color:"plum",name:"Plum",lines:["I SPEAK","FLUENT BINARY"]},
  {id:"shirt-navy-slogan-v1",color:"navy",name:"Navy",lines:["TRUST ME,","I'M COMPILING"]},
  {id:"shirt-forest-slogan-v1",color:"forest",name:"Forest",lines:["IT'S NOT A BUG","IT'S A FEATURE"]},
  {id:"shirt-maroon-slogan-v1",color:"maroon",name:"Maroon",lines:["COBOL","NEVER DIES"]},
  {id:"shirt-mustard-slogan-v1",color:"mustard",name:"Mustard",lines:["GOT RAM?"]},
  {id:"shirt-charcoal-slogan-v1",color:"charcoal",name:"Charcoal",lines:["404:","SLEEP NOT FOUND"]},
  {id:"shirt-rust-slogan-v1",color:"rust",name:"Rust",lines:["sudo","make money"]},
  {id:"shirt-steel-blue-slogan-v1",color:"steel-blue",name:"Steel Blue",lines:["WORKS ON","MY MACHINE"]},
  {id:"shirt-olive-slogan-v1",color:"olive",name:"Olive",lines:["KEEP CALM","AND REBOOT"]},
  {id:"shirt-cranberry-slogan-v1",color:"cranberry",name:"Cranberry",lines:["CTRL + ALT","+ COFFEE"]},
  {id:"shirt-slate-slogan-v1",color:"slate",name:"Slate",lines:["OUT OF MEMORY","NOT AMBITION"]},
  {id:"shirt-copper-slogan-v1",color:"copper",name:"Copper",lines:["POWERED BY","POOR DECISIONS"]},
  {id:"shirt-dusty-rose-slogan-v1",color:"dusty-rose",name:"Dusty Rose",lines:["FINANCIALLY","UNDERFUNDED.","SARCASTICALLY","OVERQUALIFIED."]}
].map(s => Object.freeze({...s, phrase:s.lines.join(" "),lines:Object.freeze(s.lines)})));
