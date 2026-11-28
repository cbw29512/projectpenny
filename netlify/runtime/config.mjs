// Explicit private-beta configuration. Never fall back to NETLIFY_DB_URL.
const ROLE=/^[a-z][a-z0-9_]{0,62}$/;
const KEY=/^[a-f0-9]{64,128}$/;
export function loadRuntime(env) {
  if(env.PENNY_GATEWAY_ENABLED!=="true" || env.CONTEXT!=="production")
    return null;
  const origin=env.PENNY_ORIGIN;
  if(typeof origin!=="string" || !origin.startsWith("https://") ||
     new URL(origin).origin!==origin) throw new Error("invalid origin");
  const roles={member:env.PENNY_MEMBER_DB_ROLE,bridge:env.PENNY_BRIDGE_DB_ROLE};
  const urls={member:env.PENNY_MEMBER_DB_URL,bridge:env.PENNY_BRIDGE_DB_URL};
  if(!Object.values(roles).every(x=>typeof x==="string"&&ROLE.test(x)) ||
     roles.member===roles.bridge) throw new Error("separate roles required");
  for(const scope of ["member","bridge"]) {
    const url=new URL(urls[scope]);
    // No URI options can override TLS or connection policy.
    if(!["postgres:","postgresql:"].includes(url.protocol) ||
       url.search || url.hash || !url.hostname || !url.password ||
       decodeURIComponent(url.username)!==roles[scope] ||
       url.pathname.length<2) throw new Error("invalid scoped connection");
  }
  if(typeof env.PENNY_MEMBER_KEY_HEX!=="string" || !KEY.test(env.PENNY_MEMBER_KEY_HEX) ||
     typeof env.PENNY_BRIDGE_KEY_HEX!=="string" || !KEY.test(env.PENNY_BRIDGE_KEY_HEX) ||
     env.PENNY_MEMBER_KEY_HEX===env.PENNY_BRIDGE_KEY_HEX ||
     env.PENNY_MEMBER_KEY_HEX.length%2 || env.PENNY_BRIDGE_KEY_HEX.length%2)
    throw new Error("separate keys required");
  return {origin,roles,urls,memberKey:Buffer.from(env.PENNY_MEMBER_KEY_HEX,"hex"),
    bridgeKey:Buffer.from(env.PENNY_BRIDGE_KEY_HEX,"hex")};
}
