"use client";

// Grouped parameter rail. Params are bucketed by `param.group`; an
// "Ungrouped" bucket holds anything without a group= annotation and
// renders last. Group order within each .scad is first-occurrence
// order (so the author controls the rail's top-to-bottom flow from
// source).
//
// Groups are collapsible (local per-group state, defaults open).
// Chevron icon rotates between closed/open.

import clsx from "clsx";
import { useMemo, useState } from "react";
import { ParamRow } from "./ParamRow";
import type { Param, ParamValue } from "@/lib/scad-params/parse";

const UNGROUPED_ID = "__ungrouped__";
const UNGROUPED_LABEL = "Ungrouped";

interface Props {
  params: Param[];
  values: Record<string, ParamValue>;
  onChange: (name: string, value: ParamValue) => void;
}

export function ParamRail({ params, values, onChange }: Props) {
  const groups = useMemo(() => groupParams(params), [params]);

  if (params.length === 0) {
    return (
      <p className="p-14 text-12 text-text-dim">No parameters in this model.</p>
    );
  }

  return (
    <div className="flex flex-col">
      {groups.map((g) => (
        <ParamGroup key={g.id} group={g} values={values} onChange={onChange} />
      ))}
    </div>
  );
}

function ParamGroup({
  group,
  values,
  onChange,
}: {
  group: Group;
  values: Record<string, ParamValue>;
  onChange: (name: string, value: ParamValue) => void;
}) {
  const [open, setOpen] = useState(true);
  return (
    <div className="border-b border-line">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className={clsx(
          "flex w-full items-center gap-6 px-14 py-8",
          "font-mono text-10 uppercase tracking-wide text-text-dim",
          "hover:text-text",
        )}
      >
        <Chevron open={open} />
        <span>{group.label}</span>
        <span className="text-text-mute">{group.params.length}</span>
      </button>
      {open && (
        <div className="flex flex-col gap-12 px-14 pb-12 pt-2">
          {group.params.map((p) => (
            <ParamRow
              key={p.name}
              param={p}
              value={values[p.name]}
              onChange={onChange}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      width="10"
      height="10"
      viewBox="0 0 10 10"
      aria-hidden="true"
      className={clsx(
        "text-text-mute transition-transform",
        open ? "rotate-90" : "rotate-0",
      )}
    >
      <path
        d="M3 2 L7 5 L3 8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

interface Group {
  id: string;
  label: string;
  params: Param[];
}

function groupParams(params: Param[]): Group[] {
  const order: string[] = [];
  const byId = new Map<string, Param[]>();
  let hasUngrouped = false;
  for (const p of params) {
    const id = p.group ?? UNGROUPED_ID;
    if (id === UNGROUPED_ID) hasUngrouped = true;
    if (!byId.has(id)) {
      byId.set(id, []);
      if (id !== UNGROUPED_ID) order.push(id);
    }
    byId.get(id)!.push(p);
  }
  const groups: Group[] = order.map((id) => ({
    id,
    label: humanize(id),
    params: byId.get(id)!,
  }));
  if (hasUngrouped) {
    groups.push({
      id: UNGROUPED_ID,
      label: UNGROUPED_LABEL,
      params: byId.get(UNGROUPED_ID)!,
    });
  }
  return groups;
}

function humanize(slug: string): string {
  return slug.charAt(0).toUpperCase() + slug.slice(1).replaceAll("_", " ");
}
