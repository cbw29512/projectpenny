import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createActivityReader} from "../../website/assets/activity-reader.mjs";
import {bindActivityReader} from "../../website/assets/activity-reader-render.mjs";
const json=(body,status=200,headers={})=>new Response(JSON.stringify(body),{status,
  headers:{"Content-Type":"application/json",...headers}});
function fixture(responses){
  let now=1000000;const calls=[];
  const reader=createActivityReader({enabled:true,clock:()=>now,fetcher:async(path,opts)=>{
    calls.push([path,opts]);return responses.shift();
  }});
  return {reader,calls,advance:ms=>{now+=ms;}};
}
test("manual read, bounded cadence, historical labeling and expiry",async()=>{
  assert.throws(()=>createActivityReader());
  const f=fixture([json({sampled_at:999,activity:"working"})]);
  assert.equal(f.calls.length,0);
  await f.reader.read();
  assert.equal(f.reader.snapshot().view.label,"Last observed: Working");
  assert.equal(f.calls[0][0],"/api/v1/activity");
  assert.equal(f.calls[0][1].credentials,"omit");
  assert.equal(f.calls[0][1].redirect,"error");
  await f.reader.read();assert.equal(f.calls.length,1);
  f.advance(119000);assert.equal(f.reader.snapshot().view,null);
  assert.equal(f.calls.length,1);
});
test("regression, conflicting replay, throttle and malformed content fail closed",async()=>{
  const f=fixture([json({sampled_at:1000,activity:"working"}),
    json({sampled_at:1000,activity:"idle"}),json({sampled_at:999,activity:"idle"}),
    json({status:"rate_limited"},429,{"Retry-After":"300"}),json({sampled_at:1479,activity:"idle",secret:"x"})]);
  await f.reader.read();f.advance(60000);await f.reader.read();
  assert.equal(f.reader.snapshot().view,null);
  f.advance(60000);await f.reader.read();assert.equal(f.reader.snapshot().view,null);
  f.advance(60000);await f.reader.read();f.advance(60000);
  await f.reader.read();assert.equal(f.calls.length,4);
  f.advance(240000);await f.reader.read();assert.equal(f.reader.snapshot().view,null);
  assert.equal(f.calls.length,5);
});
test("oversized and late response cannot display",async()=>{
  const f=fixture([json({sampled_at:1000,activity:"x".repeat(600)})]);
  await f.reader.read();assert.equal(f.reader.snapshot().view,null);
  let finish;
  const reader=createActivityReader({enabled:true,clock:()=>1000000,
    fetcher:()=>new Promise(resolve=>{finish=resolve;})});
  const pending=reader.read();reader.close();
  finish(json({sampled_at:1000,activity:"working"}));await pending;
  assert.equal(reader.snapshot().view,null);
  assert.equal(reader.snapshot().canRefresh,false);
});
test("renderer is historical and public preview stays disconnected",async()=>{
  const f=fixture([json({sampled_at:1000,activity:"off_duty"})]);
  const label={},stamp={},refresh={addEventListener:(name,fn)=>refresh.click=fn};
  const view=bindActivityReader({label,stamp,refresh},f.reader);
  await refresh.click();
  assert.equal(label.textContent,"Last observed: Off duty");
  assert.equal(stamp.textContent,"1970-01-01T00:16:40.000Z");
  assert.equal(refresh.disabled,true);
  view.close();assert.equal(stamp.textContent,"");
  const root=path=>readFileSync(new URL("../../"+path,import.meta.url),"utf8");
  assert.doesNotMatch(root("website/index.html"),/activity-reader\.mjs|activity-reader-render\.mjs/);
  assert.match(root("website/_headers"),/connect-src 'none'/);
  assert.match(root("private-beta/index.html"),/id="beta-activity-refresh" type="button" disabled/);
});
