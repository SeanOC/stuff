"use client";

// Single-slot modal stack. Only one modal can be open at a time — the
// discriminated union makes "two modals open at once" impossible to
// express, which cuts a whole class of focus/Escape/backdrop bugs at
// the type level. See phase-3 plan D4.
//
// Consumers:
//   const { modal, dispatch } = useUI();
//   if (modal.kind === "palette") ...
//   dispatch({ type: "open", modal: { kind: "palette" } });
//   dispatch({ type: "close" });
//
// UIContext also carries an optional `detail` bridge: the active
// DetailPage publishes its command-palette-relevant handles here so
// the palette — which lives at AppShell level — can surface
// detail-specific commands (Download STL, Save preset, presets) when
// the user is on a model page (st-3lc). DetailPage clears the slot on
// unmount so palette never holds a stale handle.

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useReducer,
  type ReactNode,
} from "react";
import type { Preset } from "@/lib/scad-params/parse";

export type Modal =
  | { kind: "none" }
  | { kind: "palette" }
  | { kind: "errorLog"; log: string }
  | { kind: "shortcutSheet" };

export interface DetailBridge {
  slug: string;
  title: string;
  /** Stock + user presets, flat list. `isUser` flag lets callers style. */
  presets: Array<Preset & { isUser: boolean }>;
  canDownload: boolean;
  downloadStl: () => void;
  loadPreset: (id: string) => void;
  openSaveRow: () => void;
}

export type UIAction =
  | { type: "open"; modal: Modal }
  | { type: "close" }
  | { type: "setDetail"; detail: DetailBridge | null };

interface UIState {
  modal: Modal;
  detail: DetailBridge | null;
}

const initialState: UIState = { modal: { kind: "none" }, detail: null };

function reducer(state: UIState, action: UIAction): UIState {
  switch (action.type) {
    case "open":
      return { ...state, modal: action.modal };
    case "close":
      return { ...state, modal: { kind: "none" } };
    case "setDetail":
      return { ...state, detail: action.detail };
  }
}

interface UIContextValue {
  modal: Modal;
  detail: DetailBridge | null;
  dispatch: (action: UIAction) => void;
  /** Convenience wrappers — pre-built callbacks so consumers don't
   *  re-create function identities on every render. */
  openModal: (modal: Modal) => void;
  closeModal: () => void;
  setDetail: (detail: DetailBridge | null) => void;
}

const UIContext = createContext<UIContextValue | null>(null);

export function UIProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const openModal = useCallback(
    (modal: Modal) => dispatch({ type: "open", modal }),
    [],
  );
  const closeModal = useCallback(() => dispatch({ type: "close" }), []);
  const setDetail = useCallback(
    (detail: DetailBridge | null) => dispatch({ type: "setDetail", detail }),
    [],
  );
  const value = useMemo<UIContextValue>(
    () => ({
      modal: state.modal,
      detail: state.detail,
      dispatch,
      openModal,
      closeModal,
      setDetail,
    }),
    [state.modal, state.detail, openModal, closeModal, setDetail],
  );
  return <UIContext.Provider value={value}>{children}</UIContext.Provider>;
}

export function useUI(): UIContextValue {
  const ctx = useContext(UIContext);
  if (!ctx) {
    throw new Error("useUI must be used inside a <UIProvider>");
  }
  return ctx;
}
