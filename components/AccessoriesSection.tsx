"use client";

// "Accessories" — static STL files that pair with this model via the
// catalog's M:N compatibleModels relation (st-bao). Heading style
// matches the surrounding metadata sections (Source / Render log /
// Warnings) so accessories read as additional metadata rather than
// competing with the main download flow.

import clsx from "clsx";

export interface DetailPageAccessory {
  slug: string;
  title: string;
  blurb: string;
  downloadUrl: string;
  fileSize: number;
  attribution?: string;
}

interface Props {
  accessories: DetailPageAccessory[];
}

export function AccessoriesSection({ accessories }: Props) {
  if (accessories.length === 0) return null;
  return (
    <section data-testid="accessories-section" className="mt-18">
      <div className="font-mono text-10 uppercase tracking-wide text-text-mute">
        Accessories
      </div>
      <ul className="mt-6 flex flex-col gap-8">
        {accessories.map((a) => (
          <li
            key={a.slug}
            data-testid="accessory-row"
            className="flex flex-col gap-3"
          >
            <div className="text-11 font-semibold text-text">{a.title}</div>
            <div className="text-10 text-text-dim">{a.blurb}</div>
            <div className="flex items-center gap-8">
              <a
                href={a.downloadUrl}
                download={`${a.slug}.stl`}
                className={clsx(
                  "inline-flex items-center rounded-3 border border-line bg-panel2 px-6 py-1",
                  "font-mono text-10 text-text no-underline",
                  "hover:bg-panel-hi hover:text-text",
                )}
              >
                Download STL
              </a>
              <span className="font-mono text-10 text-text-mute">
                {formatFileSize(a.fileSize)}
              </span>
            </div>
            {a.attribution && (
              <div className="text-10 italic text-text-mute">{a.attribution}</div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  const mb = kb / 1024;
  return `${mb.toFixed(1)} MB`;
}
