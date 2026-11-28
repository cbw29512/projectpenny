import test from "node:test";
import assert from "node:assert/strict";
import {randomUUID} from "node:crypto";
import {createLimiter} from "../../netlify/gateway/limiter.mjs";
const owner=randomUUID();
const member={scope:"member",subject:owner};
const bridge={scope:"bridge",subject:"nucbox-bridge"};

test("separate scoped parameterized attempts",async()=>{
  const calls=[];
  const limiter=createLimiter({
    memberQuery:async(s,a)=>{calls.push(["member",s,a]);return [{ok:true}];},
    bridgeQuery:async(s,a)=>{calls.push(["bridge",s,a]);return [{ok:false}];},
  });
  assert.equal(await limiter(member,"submit"),true);
  assert.equal(await limiter(bridge,"claim"),false);
  assert.deepEqual(calls[0][2],[owner,"submit"]);
  assert.deepEqual(calls[1][2],["claim"]);
  assert.ok(!calls[0][1].includes(owner));
});
test("forged scope and unknown operation never touch database",async()=>{
  const query=async()=>{throw Error("must not call");};
  const limiter=createLimiter({memberQuery:query,bridgeQuery:query});
  for(const [identity,op] of [[member,"claim"],[bridge,"read"],
    [{scope:"bridge",subject:owner},"claim"],[{scope:"member",subject:"forged"},"submit"]])
    assert.equal(await limiter(identity,op),false);
});
test("malformed counter response and outage fail closed",async()=>{
  for(const query of [async()=>[],async()=>[{ok:"true"}],async()=>{throw Error("outage");}]) {
    const limiter=createLimiter({memberQuery:query,bridgeQuery:query});
    await assert.rejects(limiter(member,"read"));
  }
});
