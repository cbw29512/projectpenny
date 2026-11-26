import { LAYERS, OUTFIT, parseWorld, acceptWorld } from "./world-state.mjs";

// Resolve only static DOM nodes. Snapshot data never becomes an attribute,
// selector, URL, style or markup. Missing nodes prevent partial updates.
export function worldRenderer(scene, notice) {
  const base = scene.querySelector("[data-world-base]");
  const nodes = new Map(LAYERS.map(id => [id,
    scene.querySelector('[data-world-layer="' + id + '"]')]));
  if (!base || [...nodes.values()].some(node => !node)
      || new Set([base, ...nodes.values()]).size !== LAYERS.length + 1)
    throw new Error("world scene incomplete");
  let current = null;
  return text => {
    try {
      const result = acceptWorld(current, parseWorld(text));
      if (!result.accepted) {
        notice.textContent = current
          ? "Last reviewed virtual scene · revision " + current.revision + " · update unavailable."
          : "Fixed concept scene · no reviewed world snapshot connected.";
        return false;
      }
      const visible = new Set(result.state.layers);
      for (const [id, node] of nodes) node.hidden = !visible.has(id);
      base.hidden = visible.has(OUTFIT);
      current = result.state;
      notice.textContent = "Reviewed virtual preview · revision " + current.revision
        + " · not live activity or real purchases.";
      return true;
    } catch {
      console.error("Penny world render failed.");
      notice.textContent = "World update unavailable.";
      return false;
    }
  };
}

function boot() {
  const scene = document.getElementById("penny-scene");
  const notice = document.getElementById("world-notice");
  const source = document.getElementById("world-snapshot");
  if (!scene || !notice || !source) return;
  const render = worldRenderer(scene, notice);
  const refresh = () => render(source.textContent);
  window.addEventListener("pageshow", refresh);
  refresh();
}
try { if (typeof document !== "undefined") boot(); }
catch { console.error("Penny world initialization failed."); }
