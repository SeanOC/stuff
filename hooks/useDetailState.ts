"use client";

// Detail-page state: params, camera/grid/dims toggles, and (new in
// phase 3) the preset binding.
//
// Preset binding is a nullable pair (`activePresetId` + `modified`)
// rather than a discriminated union — two states don't warrant a DU,
// and `activePresetId=null, modified=true` is a real case (user
// edited without a bound preset). See phase-3 plan D6.

import { useCallback, useMemo, useRef, useState } from "react";
import {
  defaultsOf,
  type Param,
  type ParamValue,
  type Preset,
} from "@/lib/scad-params/parse";
import { useLocalStorage } from "@/hooks/useLocalStorage";

export type CameraPreset = "top" | "front" | "iso";

export interface UserPreset {
  id: string;
  label: string;
  values: Record<string, ParamValue>;
  /** ISO timestamp of save — used only for sorting/debug. */
  savedAt: string;
}

export interface DetailState {
  params: Record<string, ParamValue>;
  camera: CameraPreset;
  showGrid: boolean;
  showDims: boolean;
  activePresetId: string | null;
  modified: boolean;
}

export interface UseDetailStateArgs {
  params: Param[];
  stockPresets: Preset[];
  slug: string;
  /**
   * Values hydrated from the URL share-string (?d=70&c=0.25&...).
   * When provided, they override per-param defaults on mount but are
   * applied only to keys listed — unlisted params keep their defaults.
   * Priority on mount: initialValues > defaults. (localStorage-backed
   * last-edited recall is deferred to a future bead.)
   */
  initialValues?: Partial<Record<string, ParamValue>>;
}

export interface UseDetailStateReturn {
  state: DetailState;
  allPresets: Array<Preset & { isUser: boolean }>;
  userPresets: UserPreset[];
  setParam: (name: string, value: ParamValue) => void;
  setCamera: (camera: CameraPreset) => void;
  toggleGrid: () => void;
  toggleDims: () => void;
  loadPreset: (id: string) => void;
  loadPresetByIndex: (oneBasedIndex: number) => void;
  saveAsPreset: (label: string) => void;
  deleteUserPreset: (id: string) => void;
}

export function useDetailState({
  params,
  stockPresets,
  slug,
  initialValues,
}: UseDetailStateArgs): UseDetailStateReturn {
  const initialParams = useMemo<Record<string, ParamValue>>(
    () => {
      const defaults = defaultsOf(params);
      if (!initialValues) return defaults;
      for (const [k, v] of Object.entries(initialValues)) {
        if (v !== undefined) defaults[k] = v;
      }
      return defaults;
    },
    // initialValues is a server-provided object; its identity is
    // stable for the mount, and we deliberately don't re-apply on
    // every render — rereading a URL mid-session would clobber the
    // user's edits.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [params],
  );
  const [values, setValues] = useState<Record<string, ParamValue>>(initialParams);
  const [camera, setCamera] = useState<CameraPreset>("iso");
  const [showGrid, setShowGrid] = useState(true);
  const [showDims, setShowDims] = useState(false);
  const [activePresetId, setActivePresetId] = useState<string | null>(null);
  const [modified, setModified] = useState(false);
  const [userPresets, setUserPresets] = useLocalStorage<UserPreset[]>(
    `stuff.v1.presets.${slug}`,
    [],
  );

  // Stable refs so the mutator callbacks don't need to list the
  // entire preset universe in their deps.
  const stockRef = useRef(stockPresets);
  stockRef.current = stockPresets;
  const userRef = useRef(userPresets);
  userRef.current = userPresets;
  const paramsRef = useRef(params);
  paramsRef.current = params;
  const activeRef = useRef(activePresetId);
  activeRef.current = activePresetId;

  const allPresets = useMemo(
    () => [
      ...stockPresets.map((p) => ({ ...p, isUser: false })),
      ...userPresets.map((p) => ({
        id: p.id,
        label: p.label,
        values: p.values,
        isUser: true,
      })),
    ],
    [stockPresets, userPresets],
  );

  const findPreset = useCallback((id: string) => {
    return (
      stockRef.current.find((p) => p.id === id) ??
      userRef.current.find((p) => p.id === id)
    );
  }, []);

  const setParam = useCallback((name: string, value: ParamValue) => {
    setValues((prev) => {
      const next = { ...prev, [name]: value };
      const active = activeRef.current
        ? findPreset(activeRef.current)
        : undefined;
      setModified(
        active ? !paramsEqual(next, active.values, paramsRef.current) : true,
      );
      return next;
    });
  }, [findPreset]);

  const toggleGrid = useCallback(() => setShowGrid((g) => !g), []);
  const toggleDims = useCallback(() => setShowDims((d) => !d), []);

  const loadPreset = useCallback(
    (id: string) => {
      const preset = findPreset(id);
      if (!preset) return;
      // Preset values are partial — fall back to the current value per
      // param so unreferenced knobs keep their state. (Stock presets
      // typically cover every param, but user presets may not.)
      setValues((prev) => {
        const defaults = defaultsOf(paramsRef.current);
        return { ...defaults, ...prev, ...preset.values };
      });
      setActivePresetId(id);
      setModified(false);
    },
    [findPreset],
  );

  const loadPresetByIndex = useCallback(
    (oneBasedIndex: number) => {
      // Stock presets come first, user presets after; index wraps to
      // that flat list. Out-of-range is a no-op (⌘5 on a model with
      // three presets shouldn't error).
      const flat = [...stockRef.current, ...userRef.current];
      const target = flat[oneBasedIndex - 1];
      if (target) loadPreset(target.id);
    },
    [loadPreset],
  );

  const saveAsPreset = useCallback(
    (rawLabel: string) => {
      const label = rawLabel.trim();
      if (!label) return;
      const id = `user-${slugify(label)}-${Date.now()}`;
      const snapshot: UserPreset = {
        id,
        label,
        values: { ...values },
        savedAt: new Date().toISOString(),
      };
      setUserPresets((prev) => [...prev, snapshot]);
      setActivePresetId(id);
      setModified(false);
    },
    [values, setUserPresets],
  );

  const deleteUserPreset = useCallback(
    (id: string) => {
      setUserPresets((prev) => prev.filter((p) => p.id !== id));
      if (activeRef.current === id) {
        setActivePresetId(null);
        setModified(true);
      }
    },
    [setUserPresets],
  );

  const state: DetailState = useMemo(
    () => ({
      params: values,
      camera,
      showGrid,
      showDims,
      activePresetId,
      modified,
    }),
    [values, camera, showGrid, showDims, activePresetId, modified],
  );

  return {
    state,
    allPresets,
    userPresets,
    setParam,
    setCamera,
    toggleGrid,
    toggleDims,
    loadPreset,
    loadPresetByIndex,
    saveAsPreset,
    deleteUserPreset,
  };
}

// Exhaustive per-param equality. Plain `===` — no float-tolerance
// epsilon. The inline-numeric input lets users type 46.0 vs 46;
// when that surfaces as a real "always-modified" bug we'll add
// kind-aware comparison. Until then, simplicity wins (plan D6).
export function paramsEqual(
  a: Record<string, ParamValue>,
  b: Record<string, ParamValue>,
  params: Param[],
): boolean {
  for (const p of params) {
    if (a[p.name] !== b[p.name]) return false;
  }
  return true;
}

function slugify(label: string): string {
  return label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40) || "preset";
}
