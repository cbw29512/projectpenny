// Candidate community wire format; deliberately not registered as a live route.
import { exact, isId, isText } from "../gateway/state.mjs";

export function validateSuggestion(body) {
  try {
    if (!exact(body, ["key", "text"]) || !isId(body.key) || !isText(body.text, 500))
      return false;
    // Match private screening: reject controls before Unicode normalization.
    if (/\p{C}/u.test(body.text)) return false;
    const normalized = body.text.normalize("NFKC").trim().replace(/\s+/gu, " ");
    return Array.from(normalized).length <= 500 &&
      (normalized.match(/[\p{L}\p{N}]/gu) ?? []).length >= 3;
  } catch {
    return false;
  }
}

// Candidate transfer envelope. The local bridge must independently authenticate
// the owner, validate the body and persist its receipt before acknowledging.
// Epoch seconds are explicit integers, never browser-controlled dates.
export function validateClaim(body, now) {
  try {
    return Number.isSafeInteger(now) && now >= 0 &&
      exact(body, ["id", "owner", "key", "text", "fence", "expiresAt", "leaseUntil"]) &&
      [body.id, body.owner, body.key, body.fence].every(isId) &&
      validateSuggestion({key: body.key, text: body.text}) &&
      Number.isSafeInteger(body.expiresAt) && Number.isSafeInteger(body.leaseUntil) &&
      now < body.leaseUntil && body.leaseUntil <= body.expiresAt &&
      body.leaseUntil - now <= 900 && body.expiresAt - now <= 3600;
  } catch {
    return false;
  }
}
