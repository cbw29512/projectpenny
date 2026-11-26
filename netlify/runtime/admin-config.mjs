// Independent opt-in; no ambient owner credentials or member/bridge reuse.
export function loadAdminRuntime(env) {
  if(env.CONTEXT!=="production" || env.PENNY_ADMIN_ENABLED!=="true") return null;
  const origin=env.PENNY_ORIGIN;
  if(typeof origin!=="string" || !origin.startsWith("https://") ||
     new URL(origin).origin!==origin) throw new Error("invalid origin");
  const roles=[env.PENNY_ADMIN_DB_ROLE,env.PENNY_MEMBER_DB_ROLE,env.PENNY_BRIDGE_DB_ROLE];
  if(!roles.every(x=>typeof x==="string" && /^[a-z][a-z0-9_]{0,62}$/.test(x)) ||
     new Set(roles).size!==3) throw new Error("separate roles required");
  const url=new URL(env.PENNY_ADMIN_DB_URL);
  if(!["postgres:","postgresql:"].includes(url.protocol) || url.search || url.hash ||
     !url.hostname || !url.password || decodeURIComponent(url.username)!==roles[0] ||
     url.pathname.length<2) throw new Error("invalid admin connection");
  return {origin,role:roles[0],url:env.PENNY_ADMIN_DB_URL};
}
