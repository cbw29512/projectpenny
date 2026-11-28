import test from "node:test";
import assert from "node:assert/strict";
import {createHmac} from "node:crypto";
import {createWorkshopVerifier} from "../../netlify/projection/workshop-state.mjs";
import {createWorkshopHandler} from "../../netlify/projection/workshop-handler.mjs";
import {createWorkshopRepository} from "../../netlify/projection/workshop-repository.mjs";
const key=Buffer.alloc(32,7),origin="https://penny.example",now=1000;
const value={sampled_at:999,stage:"prototype_reviewed",generated_at:950,expires_at:1050};
const sign=v=>"PennyWorkshop v1."+createHmac("sha256",key)
  .update("penny-workshop-publish-v1."+[v.sampled_at,v.stage,v.generated_at,v.expires_at].join(".")).digest("hex");
const req=(v=value,auth=sign(v))=>new Request(origin+"/api/v1/bridge/workshop",{method:"POST",
  headers:{Authorization:auth,"Content-Type":"application/json"},body:JSON.stringify(v)});
const read=()=>new Request(origin+"/api/v1/workshop");
function fixture(changes={}){
  let current=null;
  const handler=createWorkshopHandler({enabled:true,origin,now:()=>now,verify:createWorkshopVerifier(key),
    allow:async()=>true,repository:{publish:async v=>{current=v;return true;},read:async()=>current},...changes});
  return handler;
}
test("authenticated reviewed status and signed withdrawal",async()=>{
  const handler=fixture();
  assert.equal((await handler(req())).status,200);
  const response=await handler(read());
  assert.match(response.headers.get("cache-control"),/no-store/);
  assert.deepEqual(await response.json(),{schema:"penny-workshop-v1",status:"reviewed",
    product:"packing-checklist-v1",stage:value.stage,generated_at:950,expires_at:1050});
  const clear={sampled_at:1000,stage:"unavailable",generated_at:0,expires_at:0};
  assert.equal((await handler(req(clear))).status,200);
  assert.equal((await (await handler(read())).json()).status,"unavailable");
});
test("tampering, stale data, private fields and disabled or rate limited gate",async()=>{
  const handler=fixture();
  for(const v of [{...value,stage:"revision_reviewed"},{...value,private:"secret"},
    {...value,expires_at:1200},{...value,sampled_at:980}]){
    assert.equal((await handler(req(v,sign(value)))).status,401);
  }
  assert.equal((await handler(req(value,"PennyActivity v1."+"a".repeat(64)))).status,401);
  assert.equal((await fixture({enabled:false})(read())).status,503);
  assert.equal((await fixture({allow:async()=>false})(req())).status,429);
  const stale=fixture({repository:{publish:async()=>true,read:async()=>({...value,expires_at:1000})}});
  assert.equal((await (await stale(read())).json()).status,"unavailable");
});
test("repository scopes use fixed SQL and normalize bigint clocks",async()=>{
  const calls=[];
  const repo=createWorkshopRepository({writerQuery:async(...args)=>{calls.push(args);return [{ok:true}];},
    readerQuery:async(...args)=>{calls.push(args);return [{...value,sampled_at:"999",generated_at:"950",expires_at:"1050"}];}});
  assert.equal(await repo.publish(value),true);
  assert.deepEqual(await repo.read(),value);
  assert.deepEqual(calls[0][1],[999,"prototype_reviewed",950,1050]);
  assert.deepEqual(calls[1][1],[]);
});
