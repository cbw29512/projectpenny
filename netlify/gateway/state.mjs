// Fixed route vocabulary and bounded wire schema. Not deployed functions.
export const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
export const isId = x => typeof x === "string" && UUID.test(x) &&
  x !== "00000000-0000-0000-0000-000000000000";
export const isText = (x,n) => typeof x === "string" && x.trim().length > 0 &&
  Array.from(x).length <= n && Buffer.byteLength(x,"utf8") <= n*4 &&
  !x.includes("\0") && Buffer.from(x,"utf8").toString("utf8") === x;
export const exact = (x,keys) => x !== null && typeof x === "object" &&
  !Array.isArray(x) && Object.keys(x).length === keys.length &&
  keys.every(k => Object.hasOwn(x,k));

export function route(method,path) {
  if (method === "POST" && path === "/api/v1/questions")
    return {scope:"member",op:"submit",max:10000};
  if (method === "GET" && path.startsWith("/api/v1/questions/")) {
    const id=path.slice("/api/v1/questions/".length);
    if (isId(id)) return {scope:"member",op:"read",id,max:0};
  }
  if (method !== "POST") return null;
  const ops={claim:256,ack:1024,answer:100000,reject:1024};
  const op=path.replace(/^\/api\/v1\/bridge\//,"");
  if (path === "/api/v1/bridge/"+op && Object.hasOwn(ops,op))
    return {scope:"bridge",op,max:ops[op]};
  return null;
}

export function validateBody(op,body) {
  switch(op) {
    case "submit": return exact(body,["key","text"]) &&
      isId(body.key) && isText(body.text,2000);
    case "claim": return exact(body,[]);
    case "ack": return exact(body,["id","fence","localTask"]) &&
      [body.id,body.fence,body.localTask].every(isId);
    case "answer": return exact(body,["id","fence","text"]) &&
      isId(body.id) && isId(body.fence) && isText(body.text,16000);
    case "reject": return exact(body,["id","fence"]) &&
      isId(body.id) && isId(body.fence);
    default: return false;
  }
}
