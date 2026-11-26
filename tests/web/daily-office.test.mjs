import test from "node:test";
import assert from "node:assert/strict";
import { dailyOfficeStyle, parseDailyOffice, acceptDailyOffice, describeOffice } from "../../website/assets/scene/daily-office.mjs";
import { officePresenter } from "../../website/assets/scene/daily-office-render.mjs";

const date=i=>new Date(Date.UTC(2026,10,26+i)).toISOString().slice(0,10);
const row=i=>dailyOfficeStyle(date(i));
const snapshot=s=>JSON.stringify({...s,schema:"penny-daily-office-v1",status:"reviewed_virtual_preview"});
test("thirty daily posters and 210 different complete combinations",()=>{
  const styles=Array.from({length:211},(_,i)=>row(i));
  assert.equal(new Set(styles.slice(0,30).map(s=>s.posterId)).size,30);
  assert.equal(styles[0].posterId,styles[30].posterId);
  const key=s=>[s.shirtId,s.mugId,s.posterId].join("|");
  assert.equal(new Set(styles.slice(0,210).map(key)).size,210);
  assert.equal(key(styles[0]),key(styles[210]));
  assert.deepEqual(row(0),row(0));
  assert.equal(dailyOfficeStyle("2026-02-30"),null);
  assert.equal(dailyOfficeStyle(date(0),undefined,undefined,["new-room"]),null);
});
test("review requires exact known designs and refuses same-date mutation or rollback",()=>{
  const first=row(0);
  assert.deepEqual(parseDailyOffice(snapshot(first)),first);
  assert.equal(parseDailyOffice(snapshot({...first,posterId:"https://bad"})),null);
  assert.equal(parseDailyOffice(snapshot({...first,extra:true})),null);
  assert.equal(parseDailyOffice('{"status":"unavailable"}'),null);
  assert.equal(acceptDailyOffice(row(1),first),null);
  assert.equal(acceptDailyOffice(first,{...first,posterId:row(1).posterId}),null);
  assert.deepEqual(acceptDailyOffice(first,row(1)),row(1));
});
test("poster frame switches registered local art; reviewed state cannot be overwritten by demo",()=>{
  const frame={hidden:true},links={shirt:{},mug:{},poster:{}},notice={};
  const view=officePresenter(frame,links,notice);
  assert.equal(view.preview(date(0)),true);
  assert.equal(frame.hidden,false);
  assert.equal(frame.src,"/assets/scene/posters/"+row(0).posterId+".svg");
  assert.match(notice.textContent,/not live/);
  assert.equal(links.poster.textContent,describeOffice(row(0)).poster.phrase);
  assert.equal(view.review(snapshot(row(1))),true);
  const current=frame.src;
  assert.equal(view.preview(date(2)),false);
  assert.equal(view.review(snapshot(row(0))),false);
  assert.equal(frame.src,current);
  assert.match(notice.textContent,/Update unavailable/);
});
