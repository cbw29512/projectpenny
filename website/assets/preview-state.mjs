// Preview state only. No question, identity or answer is persisted.
export const MAX_QUESTION = 2000;
export const PREVIEW_NOTICE = "Preview only. Nothing is sent or saved.";

export function questionState(value) {
  if (typeof value !== "string") {
    throw new TypeError("question must be text");
  }
  return Object.freeze({
    length: value.length,
    canPreview: value.length <= MAX_QUESTION && value.trim().length > 0,
    notice: PREVIEW_NOTICE,
  });
}

export function previewQuestion(value) {
  const state = questionState(value);
  if (!state.canPreview) return state;
  // Explicitly not a successful submission or generated answer.
  return Object.freeze({
    ...state,
    notice: "Question previewed locally. Live chat is not connected; your draft was not sent.",
  });
}
