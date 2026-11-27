import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {randomUUID} from "node:crypto";
import {bindConversation} from "../../private-beta/conversation.mjs";
import {createBetaMailbox} from "../../website/assets/beta-mailbox.mjs";
const token="v1.fixture.fixture";
const id=randomUUID(),key=randomUUID();
function node(){
  const events={};
  return {value:"",textContent:"",disabled:false,addEventListener:(name,fn)=>events[name]=fn,
    fire:async name=>events[name]?.()};
}
function fixture(fetcher){
  const nodes=Object.fromEntries(["token","signIn","signOut","question","count","submit","read","next","status","answer"].map(k=>[k,node()]));
  let now=0;
  const mailbox=createBetaMailbox({enabled:true,uuid:()=>key,clock:()=>now,fetcher});
  const view=bindConversation(nodes,mailbox);
  return {nodes,view,advance:()=>{now+=15000;}};
}
const json=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{"Content-Type":"application/json"}});
test("private conversation preserves uncertain draft, displays only matching inert reply and clears",async()=>{
  const calls=[];
  const f=fixture(async(path,opts)=>{
    calls.push([path,opts.body]);
    if(calls.length===1)throw Error("lost");
    if(calls.length===2)return json({status:"accepted",id,replayed:true},202);
    return json({id,status:"answered",text:"<script>not markup</script>"});
  });
  const n=f.nodes;
  assert.equal(n.question.disabled,true);
  n.token.value=token;await n.token.fire("input");await n.signIn.fire("click");
  assert.equal(n.token.value,"");assert.match(n.status.textContent,/not yet verified/);
  assert.equal(calls.length,0);
  n.question.value="Hello";await n.question.fire("input");await n.submit.fire("click");
  assert.match(n.status.textContent,/unconfirmed/);
  assert.equal(n.question.disabled,true);assert.equal(n.question.value,"Hello");
  assert.equal(n.submit.textContent,"Retry same question");
  f.advance();await n.submit.fire("click");assert.equal(calls[0][1],calls[1][1]);
  assert.equal(n.read.disabled,false);assert.equal(n.submit.disabled,true);
  f.advance();await n.read.fire("click");
  assert.equal(n.answer.textContent,"<script>not markup</script>");
  await n.next.fire("click");assert.equal(n.question.value,"");assert.equal(n.answer.textContent,"No confirmed reply.");
  f.view.close();assert.equal(n.token.value,"");assert.equal(n.question.disabled,true);
  assert.equal(n.signIn.disabled,true);assert.match(n.status.textContent,/closed/);
});
test("sign-out during pending request clears private data and ignores late answer",async()=>{
  let finish;
  const f=fixture(()=>new Promise(resolve=>{finish=resolve;}));
  const n=f.nodes;n.token.value=token;await n.signIn.fire("click");
  n.question.value="private";await n.question.fire("input");
  const pending=n.submit.fire("click");
  assert.equal(n.signOut.disabled,false);await n.signOut.fire("click");
  finish(json({status:"accepted",id,replayed:false},202));await pending;
  assert.equal(n.question.value,"");assert.equal(n.token.value,"");
  assert.equal(n.answer.textContent,"No confirmed reply.");assert.equal(n.read.disabled,true);
});
test("beta page remains outside public deploy root and starts closed",()=>{
  const root=path=>readFileSync(new URL("../../"+path,import.meta.url),"utf8");
  assert.match(root("netlify.toml"),/publish = "website"/);
  assert.doesNotMatch(root("website/index.html"),/private-beta\/|beta-mailbox\.mjs/);
  assert.match(root("website/_headers"),/connect-src 'none'/);
  const html=root("private-beta/index.html");
  assert.match(html,/id="beta-token" type="password"[^>]*disabled/);
  for(const name of ["sign-in","sign-out","submit","read","next"])
    assert.match(html,new RegExp('id="beta-'+name+'" type="button" disabled'));
});
