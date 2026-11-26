import { nextAside } from "./character-asides.mjs";
import { MAX_QUESTION, PREVIEW_NOTICE, questionState, previewQuestion } from "./preview-state.mjs";

function boot() {
  const question = document.getElementById("question");
  const count = document.getElementById("count");
  const notice = document.getElementById("notice");
  const send = document.getElementById("preview-send");
  if (!question || !count || !notice || !send) throw new Error("preview controls missing");
  // Only initialize a local preview. Never send or store anything.
  question.maxLength = MAX_QUESTION;
  const render = state => {
    count.textContent = state.length + " / " + MAX_QUESTION;
    send.disabled = !state.canPreview;
    notice.textContent = state.notice;
  };
  question.addEventListener("input", () => {
    try { render(questionState(question.value)); }
    catch { send.disabled = true; notice.textContent = PREVIEW_NOTICE; }
  });
  const thought = document.getElementById("thought");
  let asideIndex = 0;
  send.addEventListener("click", () => {
    try {
      const state = previewQuestion(question.value);
      render(state);
      // A scripted character reaction, never an answer or fake AI progress.
      if (state.canPreview && thought) {
        const aside = nextAside(asideIndex);
        asideIndex = aside.index;
        thought.textContent = aside.text;
      }
    } catch {
      console.error("Penny local preview failed.");
      send.disabled = true;
      notice.textContent = "Preview unavailable. Nothing was sent.";
    }
  });
  render(questionState(question.value));
  question.disabled = false;
}
try { boot(); }
catch { console.error("Penny preview initialization failed."); }
