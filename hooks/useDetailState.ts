"use client";

// Minimal detail-page state. Phase 1b keeps this small on purpose —
// presets, modified-since-preset tracking, and localStorage wiring
// land in later beads. Expose only the state the current chrome
// actually reads.

import { useCallback, useMemo, useState } from "react";
import { defaultsOf, type Param, type ParamValue } from "@/lib/scad-params/parse";

export type CameraPreset = "top" | "front" | "iso";

export interface DetailState {
  params: Record<string, ParamValue>;
  camera: CameraPreset;
  showGrid: boolean;
  showDims: boolean;
}

export interface UseDetailStateReturn {
  state: DetailState;
  setParam: (name: string, value: ParamValue) => void;
  setCamera: (camera: CameraPreset) => void;
  toggleGrid: () => void;
  toggleDims: () => void;
}

export function useDetailState(params: Param[]): UseDetailStateReturn {
  const initialParams = useMemo(() => defaultsOf(params), [params]);
  const [values, setValues] = useState<Record<string, ParamValue>>(initialParams);
  const [camera, setCamera] = useState<CameraPreset>("iso");
  const [showGrid, setShowGrid] = useState(true);
  const [showDims, setShowDims] = useState(false);

  const setParam = useCallback((name: string, value: ParamValue) => {
    setValues((prev) => ({ ...prev, [name]: value }));
  }, []);
  const toggleGrid = useCallback(() => setShowGrid((g) => !g), []);
  const toggleDims = useCallback(() => setShowDims((d) => !d), []);

  const state: DetailState = useMemo(
    () => ({ params: values, camera, showGrid, showDims }),
    [values, camera, showGrid, showDims],
  );

  return { state, setParam, setCamera, toggleGrid, toggleDims };
}
