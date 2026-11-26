import test from "node:test";
import assert from "node:assert/strict";
import {randomUUID} from "node:crypto";
import {createAdminLimiter} from "../../netlify/admin/limiter.mjs";
const id=randomUUID();

test("admin attempt budget uses exact scope and parameterized values",async()=>{
  const calls=[];
  const limiter=createAdminLimiter(async(s,a)=>{calls.push([s,a]);return [{ok:true}];});
  assert.equal(await limiter(id,"status"),true);
  assert.equal(await limiter(id,"resume"),false);
  assert.equal(await limiter("forged","pause"),false);
  assert.deepEqual(calls[0][1],[id,"status"]);assert.equal(calls.length,1);
});
test("admin budget denies and fails closed on malformed result or outage",async()=>{
  assert.equal(await createAdminLimiter(async()=>[{ok:false}])(id,"pause"),false);
  for(const query of [async()=>[],async()=>[{ok:"true"}],async()=>{throw Error("down");}])
    await assert.rejects(createAdminLimiter(query)(id,"status"));
});
