import test from "node:test";
import assert from "node:assert/strict";
import {createScopedQuery} from "../../netlify/runtime/scoped-query.mjs";

test("runtime checks effective relation, column and sequence privileges before work", async()=>{
  let calls=0, released;
  const query=createScopedQuery({connect:async()=>({
    query:async(sql)=>{
      calls++;
      assert.match(sql,/has_table_privilege/);
      assert.match(sql,/has_any_column_privilege/);
      assert.match(sql,/has_sequence_privilege/);
      assert.match(sql,/c.relowner=r.oid/);
      return {rows:[{role:"member_scope",login:"member_scope",unsafe:true}]};
    },release:value=>{released=value;}
  })},"member_scope");
  await assert.rejects(query("SELECT forbidden",[]),/unsafe database principal/);
  assert.equal(calls,1);
  assert.equal(released,true);
});
