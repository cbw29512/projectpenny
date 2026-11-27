import test from "node:test";
import assert from "node:assert/strict";
import {createHmac} from "node:crypto";
import {createActivityVerifier} from "../../netlify/projection/state.mjs";
import {createActivityHandler} from "../../netlify/projection/handler.mjs";
import {createActivityRepository} from "../../netlify/projection/repository.mjs";
import {createActivityRuntime} from "../../netlify/runtime/activity.mjs";
const key=Buffer.alloc(32,7),origin="https://penny.example",now=1000;
const sample={sampled_at:999,activity:"working"};
const sign=v=>"PennyActivity v1."+createHmac("sha256",key)
  .update("penny-activity-publish-v1."+v.sampled_at+"."+v.activity).digest("hex");
function req(v=sample,auth=sign(v)){
  return new Request(origin+"/api/v1/bridge/activity",{method:"POST",
    headers:{Authorization:auth,"Content-Type":"application/json"},body:JSON.stringify(v)});
}
const read=()=>new Request(origin+"/api/v1/activity");
function fixture(changes={}){
  const calls=[];
  const handler=createActivityHandler({enabled:true,origin,now:()=>now,
    verify:createActivityVerifier(key),allow:async()=>true,repository:{
      publish:async v=>{calls.push(v);return true;},
      read:async()=>sample},...changes});
  return {handler,calls};
}
test("publisher authentication, freshness and exact schema",async()=>{
  const {handler,calls}=fixture();
  assert.equal((await handler(req())).status,200);
  for(const v of [{...sample,activity:"idle"},{...sample,sampled_at:980},{...sample,prompt:"private"}])
    assert.equal((await handler(req(v,sign(sample)))).status,401);
  assert.equal((await handler(req(sample,"Bearer fake"))).status,401);
  assert.deepEqual(calls,[sample]);
  assert.deepEqual(await (await handler(read())).json(),sample);
});
test("closed gates and stale read",async()=>{
  assert.equal((await fixture({enabled:false}).handler(req())).status,503);
  const blocked=fixture({allow:async()=>false});
  assert.equal((await blocked.handler(req())).status,429);
  assert.equal((await blocked.handler(read())).status,429);
  assert.deepEqual(blocked.calls,[]);
  const stale=fixture({repository:{publish:async()=>true,read:async()=>({...sample,sampled_at:880})}});
  assert.deepEqual(await (await stale.handler(read())).json(),{status:"unavailable"});
});
test("fixed scoped statements and bigint normalization",async()=>{
  const calls=[];
  const repo=createActivityRepository({writerQuery:async(...args)=>{calls.push(args);return [{ok:true}];},
    readerQuery:async(...args)=>{calls.push(args);return [{sampled_at:"999",activity:"working"}];}});
  assert.equal(await repo.publish(sample),true);
  assert.deepEqual(await repo.read(),sample);
  assert.deepEqual(calls[0][1],[999,"working"]);
  assert.deepEqual(calls[1][1],[]);
});
test("runtime remains closed without approved configuration",async()=>{
  const handler=createActivityRuntime({env:{CONTEXT:"deploy-preview"}});
  assert.equal((await handler(read())).status,503);
});
