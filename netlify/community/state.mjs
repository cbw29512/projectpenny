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
