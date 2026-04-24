"use client";

// Share the current param state via a copy-link or JSON download.
// Owned by DetailPage; opens through UIContext's `modal.kind ===
// "share"`. Phase-3 plan D14 — two actions only (Copy link, Download
// JSON). Short-URL service is a follow-up bead.

import { useCallback } from "react";
import clsx from "clsx";
import { Modal } from "./Modal";
import { useUI } from "@/contexts/UIContext";

interface ShareDialogProps {
  modelTitle: string;
  modelSlug: string;
  shareUrl: string;
  params: Record<string, unknown>;
  /**
   * Called after Copy link succeeds so the caller can fire a toast
   * and close the dialog. The dialog closes itself on Copy; the
   * hook exists so the caller surfaces the success cue.
   */
  onCopied: () => void;
}

export function ShareDialog({
  modelTitle,
  modelSlug,
  shareUrl,
  params,
  onCopied,
}: ShareDialogProps) {
  const { modal, dispatch } = useUI();
  const open = modal.kind === "share";
  const close = useCallback(() => dispatch({ type: "close" }), [dispatch]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      close();
      onCopied();
    } catch {
      // Clipboard API unavailable (no HTTPS / no permission) —
      // surface the URL for manual select-and-copy. No toast in
      // this branch; the textarea-fallback UX lands in a follow-up
      // bead if it turns out to matter.
    }
  }, [shareUrl, close, onCopied]);

  const handleDownload = useCallback(() => {
    const blob = new Blob(
      [JSON.stringify({ modelSlug, params }, null, 2)],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${modelSlug}-params.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    close();
  }, [modelSlug, params, close]);

  const timestamp = new Date().toISOString().slice(0, 19).replace("T", " ");

  return (
    <Modal
      open={open}
      onClose={close}
      label="Share these parameters"
      className="w-full max-w-[520px]"
    >
      <div data-testid="share-dialog" className="p-14">
        <div className="flex items-start justify-between gap-12">
          <div>
            <h2 className="m-0 text-14 font-semibold text-text">
              Share these parameters
            </h2>
            <p className="mt-4 font-mono text-10 text-text-mute">
              {modelTitle} · {timestamp} UTC
            </p>
          </div>
          <button
            type="button"
            onClick={close}
            aria-label="Close share dialog"
            className="font-mono text-11 text-text-dim hover:text-text"
          >
            ✕
          </button>
        </div>

        <div
          data-testid="share-url"
          className={clsx(
            "mt-14 overflow-hidden text-ellipsis whitespace-nowrap",
            "rounded-3 border border-line bg-panel2 px-10 py-8 font-mono text-11 text-text-dim",
          )}
          title={shareUrl}
        >
          {shareUrl}
        </div>

        <div className="mt-14 flex items-center justify-end gap-8">
          <button
            type="button"
            onClick={handleDownload}
            className={clsx(
              "rounded-3 border border-line bg-panel px-10 py-6",
              "font-mono text-11 text-text-dim hover:text-text",
            )}
          >
            Download .json
          </button>
          <button
            type="button"
            onClick={handleCopy}
            className={clsx(
              "rounded-3 border border-accent-line bg-accent px-10 py-6",
              "font-mono text-11 font-semibold text-accent-ink",
            )}
          >
            Copy link
          </button>
        </div>
      </div>
    </Modal>
  );
}
