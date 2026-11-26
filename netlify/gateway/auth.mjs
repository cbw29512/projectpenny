// Short-lived, operator-issued private beta credentials; no signup endpoint.
import {createHmac,timingSafeEqual} from "node:crypto";
import {exact,isId} from "./state.mjs";

const MAX_TTL=900;
function keyOk(key) { return Buffer.isBuffer(key) && key.length>=32; }
function signature(key,payload) {
  return createHmac("sha256",key).update("penny-beta-v1."+payload).digest();
}
function decode(s) {
  if (!/^[A-Za-z0-9_-]+$/.test(s)) throw new Error("encoding");
  const result=Buffer.from(s,"base64url");
  if(result.toString("base64url")!==s) throw new Error("encoding");
  return result;
}

export function createVerifier({memberKey,bridgeKey,now=()=>Math.floor(Date.now()/1000)}) {
  if (!keyOk(memberKey) || !keyOk(bridgeKey) || memberKey.equals(bridgeKey))
    throw new Error("separate strong credential keys required");
  // Copy buffers so a caller cannot accidentally change keys during runtime.
  const keys={member:Buffer.from(memberKey),bridge:Buffer.from(bridgeKey)};
  return (authorization,scope) => {
    try {
      if (!Object.hasOwn(keys,scope) || typeof authorization!=="string" ||
          authorization.length>1024 || !authorization.startsWith("Bearer ")) return null;
      const parts=authorization.slice(7).split(".");
      if(parts.length!==3 || parts[0]!=="v1") return null;
      const [_,payload,encodedSig]=parts;
      const sig=decode(encodedSig), expected=signature(keys[scope],payload);
      if(sig.length!==expected.length || !timingSafeEqual(sig,expected)) return null;
      const c=JSON.parse(decode(payload).toString("utf8"));
      const t=now();
      if(!exact(c,["aud","sub","iat","exp"]) || c.aud!==scope ||
         !Number.isSafeInteger(t) || !Number.isSafeInteger(c.iat) ||
         !Number.isSafeInteger(c.exp) || c.iat>t || c.exp<=t ||
         c.exp<=c.iat || c.exp-c.iat>MAX_TTL ||
         (scope==="member" ? !isId(c.sub) : c.sub!=="nucbox-bridge")) return null;
      return Object.freeze({scope,subject:c.sub});
    } catch {
      // Never log credentials or token contents.
      return null;
    }
  };
}
