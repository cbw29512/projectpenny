import test from "node:test";
import assert from "node:assert/strict";
import {randomUUID} from "node:crypto";
import {readFileSync} from "node:fs";
import {bindHomeConversation} from "../../website/assets/home-conversation.mjs";
const id=randomUUID(),key=randomUUID();
function node(){
  const events={};
  return {value:"",textContent:"",disabled:true,hidden:true,dataset:{},
    addEventListener:(name,fn)=>events[name]=fn,fire:async name=>events[name]?.()};
}
function fixture(live="false"){
  const nodes=Object.fromEntries(["home-conversation","home-beta-auth","home-beta-actions",
    "home-beta-token","home-beta-sign-in","home-beta-sign-out","question","count",
    "home-beta-submit","home-beta-read","home-beta-next","notice","welcome",
    "preview-send","speech-label"].map(k=>[k,node()]));
  nodes["home-conversation"].dataset.live=live;
  let now=0,calls=0;
  const window=node();
  const args={document:{getElementById:id=>nodes[id]},window,
    origin:"https://projectpenny.netlify.app",secure:true,uuid:()=>key,clock:()=>now,
    fetcher:async()=>new Response(JSON.stringify(++calls===1
      ?{status:"accepted",id,replayed:false}:{id,status:"answered",text:"<b>Reviewed reply</b>"}),
      {status:calls===1?202:200,headers:{"Content-Type":"application/json"}})};
  return {nodes,args,window,calls:()=>calls,advance:()=>now+=15000};
}
test("static homepage stays local only; wrong host cannot activate beta",()=>{
  const f=fixture();
  assert.equal(bindHomeConversation(f.args),null);
  assert.equal(f.calls(),0);
  f.nodes["home-conversation"].dataset.live="true";
  assert.throws(()=>bindHomeConversation({...f.args,origin:"https://other.example"}));
  assert.throws(()=>bindHomeConversation({...f.args,secure:false}));
  assert.equal(f.nodes["home-beta-auth"].hidden,true);
});
test("invitation beta uses same composer and inert speech bubble; clears on exit",async()=>{
  const f=fixture("true"),n=f.nodes;
  assert.ok(bindHomeConversation(f.args));
  assert.equal(n["preview-send"].hidden,true);
  assert.equal(n["home-beta-auth"].hidden,false);
  assert.equal(f.calls(),0);
  n["home-beta-token"].value="v1.fixture.fixture";
  await n["home-beta-sign-in"].fire("click");
  n.question.value="Hello";await n.question.fire("input");
  await n["home-beta-submit"].fire("click");
  f.advance();await n["home-beta-read"].fire("click");
  assert.equal(n.welcome.textContent,"<b>Reviewed reply</b>");
  await f.window.fire("pagehide");
  assert.equal(n.welcome.textContent,"No confirmed reply.");
  assert.equal(n.question.value,"");
  assert.equal(n["home-beta-token"].value,"");
});
test("default HTML and CSP keep invitation mode inaccessible",()=>{
  const html=readFileSync("website/index.html","utf8");
  assert.match(html,/id="home-conversation" data-live="false"/);
  assert.match(html,/id="home-beta-auth"[^>]*hidden/);
  assert.match(html,/id="home-beta-actions"[^>]*hidden/);
  assert.match(readFileSync("website/_headers","utf8"),/connect-src 'none'/);
});
