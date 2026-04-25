"use client";

// Preset list + save-row, used at the top of the param rail (st-yxj
// moved this here from the metadata left rail because picking a
// preset is conceptually "set these params"). Renders a heading row
// with a "+ save" affordance, the inline `SavePresetRow` (when
// open), and the preset list with active-highlight + modified-dot.

import { useCallback, useEffect, useRef, useState } from "react";
import clsx from "clsx";

interface Props {
  presets: Array<{ id: string; label: string; isUser: boolean }>;
  activePresetId: string | null;
  modified: boolean;
  onLoadPreset: (id: string) => void;
  onDeletePreset: (id: string) => void;
  onSavePreset: (label: string) => void;
  saveRowOpen: boolean;
  setSaveRowOpen: (open: boolean) => void;
}

export function PresetSection({
  presets,
  activePresetId,
  modified,
  onLoadPreset,
  onDeletePreset,
  onSavePreset,
  saveRowOpen,
  setSaveRowOpen,
}: Props) {
  return (
    <div className="border-b border-line bg-panel px-14 py-10">
      <div className="flex items-center justify-between">
        <span className="font-mono text-10 uppercase tracking-wide text-text-mute">
          Presets
        </span>
        <button
          type="button"
          onClick={() => setSaveRowOpen(true)}
          className="font-mono text-10 text-text-dim hover:text-text"
          aria-label="Save current params as preset"
        >
          + save
        </button>
      </div>
      {saveRowOpen && (
        <SavePresetRow
          onSave={(label) => {
            onSavePreset(label);
            setSaveRowOpen(false);
          }}
          onCancel={() => setSaveRowOpen(false)}
        />
      )}
      <ul
        data-testid="preset-list"
        className="mt-4 flex flex-col gap-2 font-mono text-11"
      >
        {presets.length === 0 && !saveRowOpen && (
          <li className="text-text-mute">—</li>
        )}
        {presets.map((p) => (
          <li
            key={p.id}
            className={clsx(
              "flex items-center justify-between gap-6 rounded-3 border border-transparent px-6 py-2",
              activePresetId === p.id
                ? "border-accent-line bg-accent-soft text-text"
                : "text-text-dim hover:border-line hover:text-text",
            )}
          >
            <button
              type="button"
              onClick={() => onLoadPreset(p.id)}
              data-preset-id={p.id}
              className="flex-1 truncate text-left"
            >
              {p.label}
              {activePresetId === p.id && modified && (
                <span
                  data-testid="modified-dot"
                  aria-label="modified since preset"
                  className="ml-6 inline-block h-2 w-2 rounded-full bg-warn"
                />
              )}
            </button>
            {p.isUser && (
              <button
                type="button"
                onClick={() => onDeletePreset(p.id)}
                aria-label={`Delete preset ${p.label}`}
                className="text-text-mute hover:text-red"
              >
                ✕
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function SavePresetRow({
  onSave,
  onCancel,
}: {
  onSave: (label: string) => void;
  onCancel: () => void;
}) {
  const [label, setLabel] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const submit = useCallback(() => {
    if (!label.trim()) return;
    onSave(label);
  }, [label, onSave]);

  return (
    <div className="mt-4 flex items-center gap-4">
      <input
        ref={inputRef}
        data-testid="save-preset-input"
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        placeholder="Preset name…"
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            submit();
          } else if (e.key === "Escape") {
            e.preventDefault();
            onCancel();
          }
        }}
        className="min-w-0 flex-1 rounded-3 border border-line bg-panel2 px-6 py-2 font-mono text-11 text-text"
      />
      <button
        type="button"
        onClick={submit}
        className="rounded-3 border border-accent-line bg-accent px-6 py-2 font-mono text-10 text-accent-ink"
      >
        save
      </button>
      <button
        type="button"
        onClick={onCancel}
        aria-label="Cancel save"
        className="font-mono text-10 text-text-mute hover:text-text"
      >
        ✕
      </button>
    </div>
  );
}
