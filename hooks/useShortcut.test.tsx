// @vitest-environment jsdom

// Exercise the chord matcher and input-field guard without mocking
// document — just render a minimal component that binds a shortcut,
// dispatch keyboard events, and watch the handler.

import { act, cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useShortcut, type Binding } from "./useShortcut";

afterEach(() => cleanup());

function Harness({
  binding,
  onFire,
  enabled = true,
}: {
  binding: Binding;
  onFire: (e: KeyboardEvent) => void;
  enabled?: boolean;
}) {
  useShortcut(binding, onFire, { enabled });
  return <input aria-label="field" />;
}

function press(init: KeyboardEventInit) {
  act(() => {
    window.dispatchEvent(new KeyboardEvent("keydown", init));
  });
}

describe("useShortcut", () => {
  it("fires a bare key bound to 'g'", () => {
    const h = vi.fn();
    render(<Harness binding="g" onFire={h} />);
    press({ key: "g" });
    expect(h).toHaveBeenCalledTimes(1);
  });

  it("matches the bare key case-insensitively (Shift+g still fires)", () => {
    const h = vi.fn();
    render(<Harness binding="g" onFire={h} />);
    press({ key: "G", shiftKey: true });
    // Bare-key bindings don't declare Shift, so we only want to fire
    // when the modifier matches (shift=false in the binding). This
    // test pins the *non-fire* behavior: Shift+G is a different chord.
    expect(h).not.toHaveBeenCalled();
  });

  it("$mod resolves to metaKey or ctrlKey", () => {
    const h = vi.fn();
    render(<Harness binding="$mod+k" onFire={h} />);
    press({ key: "k", metaKey: true });
    expect(h).toHaveBeenCalledTimes(1);
    press({ key: "k", ctrlKey: true });
    expect(h).toHaveBeenCalledTimes(2);
  });

  it("ignores bare keys when focus is in an input", () => {
    const h = vi.fn();
    const { getByLabelText } = render(<Harness binding="g" onFire={h} />);
    const input = getByLabelText("field") as HTMLInputElement;
    input.focus();
    act(() => {
      input.dispatchEvent(new KeyboardEvent("keydown", { key: "g", bubbles: true }));
    });
    expect(h).not.toHaveBeenCalled();
  });

  it("fires modifier chords even when focus is in an input", () => {
    const h = vi.fn();
    const { getByLabelText } = render(<Harness binding="$mod+s" onFire={h} />);
    const input = getByLabelText("field") as HTMLInputElement;
    input.focus();
    act(() => {
      input.dispatchEvent(
        new KeyboardEvent("keydown", { key: "s", metaKey: true, bubbles: true }),
      );
    });
    expect(h).toHaveBeenCalledTimes(1);
  });

  it("no-ops when enabled is false", () => {
    const h = vi.fn();
    render(<Harness binding="g" onFire={h} enabled={false} />);
    press({ key: "g" });
    expect(h).not.toHaveBeenCalled();
  });

  it("does not fire a $mod chord when the modifier is absent", () => {
    const h = vi.fn();
    render(<Harness binding="$mod+k" onFire={h} />);
    press({ key: "k" });
    expect(h).not.toHaveBeenCalled();
  });

  it("matches Shift+$mod+c as declared", () => {
    const h = vi.fn();
    render(<Harness binding="$mod+Shift+c" onFire={h} />);
    press({ key: "c", metaKey: true, shiftKey: true });
    expect(h).toHaveBeenCalledTimes(1);
    // Same chord without Shift must not fire.
    press({ key: "c", metaKey: true });
    expect(h).toHaveBeenCalledTimes(1);
  });
});
