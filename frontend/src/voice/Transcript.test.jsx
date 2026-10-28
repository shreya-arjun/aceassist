// @vitest-environment happy-dom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Transcript } from "./VoicePanel.jsx";
import { appendEntry } from "./voiceConfig.js";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe("Transcript", () => {
  let container, root;

  beforeEach(() => {
    // Some browsers return a Promise from scrollIntoView; a returned value from
    // an effect is treated as a cleanup function and crashes React on re-render.
    vi.spyOn(Element.prototype, "scrollIntoView").mockImplementation(() => Promise.resolve());
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    container.remove();
  });

  it("keeps rendering as new lines arrive and unmounts cleanly", () => {
    let entries = [];
    for (const [role, text] of [["agent", "Hi, I'm AceAssist."], ["user", "Do you have the AllCourt Pro 100?"], ["agent", "Yes."]]) {
      entries = appendEntry(entries, role, text);
      act(() => root.render(<Transcript entries={entries} />));
    }
    expect(container.textContent).toContain("Do you have the AllCourt Pro 100?");
    expect(container.querySelectorAll(".transcript > *").length).toBeGreaterThanOrEqual(3);
    expect(() => act(() => root.unmount())).not.toThrow();
  });
});
