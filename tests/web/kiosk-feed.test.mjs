import test from "node:test";
import assert from "node:assert/strict";
import {feedState,nextFeedOffset} from "../../kiosk/state.mjs";
test("newest tasks first and repeated polls do not reset rotation",()=>{
 const a={task_id:"a",finished_at:1,status:"succeeded"};
 const b={task_id:"b",finished_at:2,status:"failed"};
 const first=feedState(null,[a,b]);
 assert.deepEqual(first.rows,[b,a]);
 assert.equal(feedState(first.signature,[b,a]).changed,false);
 assert.equal(feedState(first.signature,[b,a,{task_id:"c",finished_at:3,status:"succeeded"}]).changed,true);
});
test("automatic feed moves down and wraps without page scrolling",()=>{
 assert.equal(nextFeedOffset(0,400,100),75);
 assert.equal(nextFeedOffset(280,400,100),300);
 assert.equal(nextFeedOffset(300,400,100),0);
 assert.equal(nextFeedOffset(0,50,100),0);
});
