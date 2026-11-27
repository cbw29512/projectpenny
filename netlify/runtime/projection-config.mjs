// Shared projection role, TLS and key validation; no environment fallbacks.
const ROLE=/^[a-z][a-z0-9_]{0,62}$/;
export function projectionConfig(env,kind){
  if(kind!=="activity"&&kind!=="workshop")throw Error("unknown projection scope");
  const flag=kind==="activity"?"PENNY_ACTIVITY_ENABLED":"PENNY_WORKSHOP_ENABLED";
  const keyField=kind==="activity"?"PENNY_PROJECTION_KEY_HEX":"PENNY_WORKSHOP_KEY_HEX";
  const otherKey=kind==="activity"?"PENNY_WORKSHOP_KEY_HEX":"PENNY_PROJECTION_KEY_HEX";
  if(env.CONTEXT!=="production"||env[flag]!=="true")return null;
  const origin=env.PENNY_ORIGIN;
  if(typeof origin!=="string"||!origin.startsWith("https://")||new URL(origin).origin!==origin)
    throw Error("invalid projection origin");
  if(kind==="workshop"&&!/^https:\/\/[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.netlify\.app$/.test(origin))
    throw Error("Workshop destination must match local Netlify host policy");
  const roles={writer:env.PENNY_PROJECTION_WRITER_DB_ROLE,reader:env.PENNY_PROJECTION_READER_DB_ROLE};
  const urls={writer:env.PENNY_PROJECTION_WRITER_DB_URL,reader:env.PENNY_PROJECTION_READER_DB_URL};
  const other=[env.PENNY_MEMBER_DB_ROLE,env.PENNY_BRIDGE_DB_ROLE,env.PENNY_ADMIN_DB_ROLE];
  if(!Object.values(roles).every(x=>typeof x==="string"&&ROLE.test(x)&&!other.includes(x))
      ||roles.writer===roles.reader)throw Error("isolated projection roles required");
  for(const name of ["writer","reader"]){
    const url=new URL(urls[name]);
    if(!["postgres:","postgresql:"].includes(url.protocol)||url.search||url.hash||!url.hostname
        ||!url.password||decodeURIComponent(url.username)!==roles[name]||url.pathname.length<2)
      throw Error("invalid projection connection");
  }
  const key=env[keyField];
  if(typeof key!=="string"||! /^[a-f0-9]{64,128}$/.test(key)||key.length%2
     ||[env.PENNY_MEMBER_KEY_HEX,env.PENNY_BRIDGE_KEY_HEX,env[otherKey]].some(x=>typeof x==="string"&&x.toLowerCase()===key))
    throw Error("separate projection key required");
  return {origin,roles,urls,key:Buffer.from(key,"hex")};
}
