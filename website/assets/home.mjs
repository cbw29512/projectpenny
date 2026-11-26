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
  const pause = document.getElementById("pause-asides");
  let asideIndex = 0;
  let timer = null;
  let paused = false;
  let pageActive = true;
  const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
  // Scene animation is independent of the request and service state.
  const rotateAside = () => {
    const aside = nextAside(asideIndex);
    asideIndex = aside.index;
    thought.textContent = aside.text;
  };
  const stopRotation = () => {
    if (timer !== null) window.clearTimeout(timer);
    timer = null;
  };
  const syncRotation = () => {
    stopRotation();
    if (!thought || !pause) return;
    pause.textContent = paused ? "Resume rotating thoughts" : "Pause rotating thoughts";
    if (motion.matches || paused || document.hidden || !pageActive) return;
    timer = window.setTimeout(() => {
      timer = null;
      try {
        if (document.hidden || paused || motion.matches || !pageActive) return;
        rotateAside();
        syncRotation();
      } catch {
        console.error("Penny thought rotation stopped.");
        stopRotation();
      }
    }, 15000);
  };
  if (thought && pause) {
    // Reduced-motion users get static dialogue; all others can pause it.
    const applyMotion = () => {
      pause.hidden = motion.matches;
      syncRotation();
    };
    pause.addEventListener("click", () => {
      paused = !paused;
      syncRotation();
    });
    motion.addEventListener("change", applyMotion);
    document.addEventListener("visibilitychange", syncRotation);
    window.addEventListener("pagehide", () => {
      pageActive = false;
      stopRotation();
    });
    window.addEventListener("pageshow", () => {
      pageActive = true;
      syncRotation();
    });
    applyMotion();
  }
  send.addEventListener("click", () => {
    try {
      const state = previewQuestion(question.value);
      render(state);
      // A scripted character reaction, never an answer or fake AI progress.
      if (state.canPreview && thought && !paused) {
        rotateAside();
        syncRotation();
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
