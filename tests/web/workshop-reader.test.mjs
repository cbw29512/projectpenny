import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createWorkshopReader} from "../../website/assets/workshop-reader.mjs";
const json=(body,status=200,headers={})=>new Response(JSON.stringify(body),{status,
  headers:{"Content-Type":"application/json",...headers}});
const reviewed=(generated=990,expires=1120,stage="prototype_reviewed")=>({
  schema:"penny-workshop-v1",status:"reviewed",product:"packing-checklist-v1",
  stage,generated_at:generated,expires_at:expires});
function fixture(responses){
  let now=1000000;const calls=[];
  const reader=createWorkshopReader({enabled:true,clock:()=>now,fetcher:async(path,opts)=>{
    calls.push([path,opts]);return responses.shift();
  }});
  return {reader,calls,advance:ms=>now+=ms};
}
test("manual same-origin read, no credentials, cooldown and lease expiry",async()=>{
  assert.throws(()=>createWorkshopReader());
  const f=fixture([json(reviewed())]);
  assert.equal(f.calls.length,0);
  await f.reader.read();
  assert.equal(f.reader.snapshot().state.stage,"prototype_reviewed");
  assert.equal(f.calls[0][0],"/api/v1/workshop");
  assert.equal(f.calls[0][1].credentials,"omit");
  assert.equal(f.calls[0][1].redirect,"error");
  await f.reader.read();assert.equal(f.calls.length,1);
  f.advance(120000);assert.equal(f.reader.snapshot().state.status,"stale");
  assert.equal(f.calls.length,1);
});
test("invalid, regressive, withdrawn and rate limited observations clear display",async()=>{
  const f=fixture([json(reviewed()),json(reviewed(989,1120)),
    json(reviewed(990,1190,"revision_reviewed")),
    json({schema:"penny-workshop-v1",status:"unavailable"}),
    json({},429,{"Retry-After":"300"}),json({...reviewed(1450,1540),private:"secret"})]);
  await f.reader.read();
  for(let i=0;i<4;i++){f.advance(60000);await f.reader.read();assert.notEqual(f.reader.snapshot().state.status,"reviewed");}
  f.advance(60000);await f.reader.read();assert.equal(f.calls.length,5);
  f.advance(240000);await f.reader.read();assert.equal(f.calls.length,6);
  assert.equal(f.reader.snapshot().state.status,"unavailable");
});
test("overlong lease, oversized response and close during pending request",async()=>{
  const f=fixture([json(reviewed(990,1121)),json({x:"x".repeat(1100)})]);
  await f.reader.read();assert.equal(f.reader.snapshot().state.status,"unavailable");
  f.advance(60000);await f.reader.read();assert.equal(f.reader.snapshot().state.status,"unavailable");
  let resolve;
  const reader=createWorkshopReader({enabled:true,clock:()=>1000000,fetcher:()=>new Promise(r=>resolve=r)});
  const pending=reader.read();reader.close();resolve(json(reviewed()));await pending;
  assert.equal(reader.snapshot().canRefresh,false);
  assert.equal(reader.snapshot().state.status,"unavailable");
});
test("deployed static preview cannot request the API by default",()=>{
  const html=readFileSync("website/index.html","utf8");
  assert.match(html,/id="workshop-refresh" type="button" data-live="false" disabled/);
  assert.match(readFileSync("website/_headers","utf8"),/connect-src 'none'/);
});
