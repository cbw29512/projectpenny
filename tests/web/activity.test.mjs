import test from "node:test";
import assert from "node:assert/strict";
import { activityView } from "../../website/assets/activity-state.mjs";
import { renderActivity } from "../../website/assets/activity-render.mjs";
const s={schema:"penny-activity-v1",status:"reviewed",state:"working",sampled_at:100,expires_at:115};
const at=(changes={},now=101)=>activityView(JSON.stringify({...s,...changes}),now);
test("activity uses fixed phrases, expires and rejects private/extra fields",()=>{
  assert.equal(at()[0],"Working");
  assert.equal(at({state:"blocked"})[0],"Recovery required");
  for(const v of [{prompt:"private"},{state:"<img>"},{expires_at:116},{sampled_at:102}])
    assert.equal(at(v)[0],"Live AI not connected");
  assert.equal(at({},115)[0],"Live AI not connected");
  const label={},thought={};
  renderActivity(label,thought,JSON.stringify(s),101);
  assert.equal(label.textContent,"Working");
});
