// Pin validated configuration to the warm handler. Never log the digest or input.
// A changed role, key, origin or connection requires a fresh process.
import {createHash} from "node:crypto";
export function runtimeFingerprint(config) {
  return createHash("sha256").update(JSON.stringify(config)).digest("hex");
}
