import test from "node:test";
import assert from "node:assert/strict";
import {createWorkshopLimiter} from "../../netlify/projection/workshop-limiter.mjs";
test("edge denial stops database work and separate operations use fixed scopes",async()=>{
  const calls=[];let allowed=false;
  const limiter=createWorkshopLimiter({edgeAllow:async()=>allowed,
    writerQuery:async(s,a)=>{calls.push(["write",s,a]);return [{ok:true}];},
    readerQuery:async(s,a)=>{calls.push(["read",s,a]);return [{ok:false}];}});
  assert.equal(await limiter("write",{}),false);
  assert.equal(calls.length,0);
  allowed=true;
  assert.equal(await limiter("invalid",{}),false);
  assert.equal(await limiter("write",{}),true);
  assert.equal(await limiter("read",{}),false);
  assert.deepEqual(calls,[["write","SELECT penny_mailbox.workshop_allow_write() AS ok",[]],
    ["read","SELECT penny_mailbox.workshop_allow_read() AS ok",[]]]);
});
test("malformed budget or unavailable edge fails closed",async()=>{
  const limit=createWorkshopLimiter({edgeAllow:async()=>true,
    writerQuery:async()=>[{ok:"true"}],readerQuery:async()=>{throw Error("fixture");}});
  await assert.rejects(limit("write",{}));
  await assert.rejects(limit("read",{}));
});
