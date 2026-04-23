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

import {
  createContext,
  useContext,
  useReducer,
  type ReactNode,
} from "react";

export type Modal =
  | { kind: "none" }
  | { kind: "palette" }
  | { kind: "share" }
  | { kind: "errorLog"; log: string }
  | { kind: "shortcutSheet" };

export type UIAction =
  | { type: "open"; modal: Modal }
  | { type: "close" };

interface UIState {
  modal: Modal;
}

const initialState: UIState = { modal: { kind: "none" } };

function reducer(state: UIState, action: UIAction): UIState {
  switch (action.type) {
    case "open":
      return { modal: action.modal };
    case "close":
      return { modal: { kind: "none" } };
  }
}

interface UIContextValue {
  modal: Modal;
  dispatch: (action: UIAction) => void;
}

const UIContext = createContext<UIContextValue | null>(null);

export function UIProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <UIContext.Provider value={{ modal: state.modal, dispatch }}>
      {children}
    </UIContext.Provider>
  );
}

export function useUI(): UIContextValue {
  const ctx = useContext(UIContext);
  if (!ctx) {
    throw new Error("useUI must be used inside a <UIProvider>");
  }
  return ctx;
}
