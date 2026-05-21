"use client";

import { useState, useCallback } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { SortablePanel } from "@/components/SortablePanel";

type Panel = { id: string; image: string };
type Status = "idle" | "loading" | "done" | "error";
type Mode = "url" | "file";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [mode, setMode] = useState<Mode>("file");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [panels, setPanels] = useState<Panel[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");
  const [pdfLoading, setPdfLoading] = useState(false);
  const [progress, setProgress] = useState("");

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const canExtract =
    status !== "loading" && (mode === "url" ? !!url.trim() : !!file);

  const runExtraction = async (fetchFn: () => Promise<Response>, defaultTitle: string) => {
    setStatus("loading");
    setError("");
    setPanels([]);
    setProgress(mode === "url" ? "Downloading video..." : "Reading video...");

    const progressMessages =
      mode === "url"
        ? ["Downloading video...", "Extracting frames...", "Detecting panel changes...", "Almost done..."]
        : ["Reading video...", "Extracting frames...", "Detecting panel changes...", "Almost done..."];

    let msgIdx = 0;
    const interval = setInterval(() => {
      msgIdx = Math.min(msgIdx + 1, progressMessages.length - 1);
      setProgress(progressMessages[msgIdx]);
    }, 8000);

    try {
      const res = await fetchFn();
      clearInterval(interval);

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Extraction failed");
      }

      const data = await res.json();
      setPanels(data.panels);
      setStatus("done");
      if (!title) setTitle(defaultTitle);
    } catch (e: any) {
      clearInterval(interval);
      setError(e.message || "Something went wrong");
      setStatus("error");
    }
  };

  const handleExtract = () => {
    if (mode === "url") {
      if (!url.trim()) return;
      const match = url.match(/[?&]v=([^&]+)/);
      const defaultTitle = match ? `Tab_${match[1]}` : "Guitar_Tab";
      runExtraction(
        () =>
          fetch(`${API_URL}/extract`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
          }),
        defaultTitle
      );
    } else {
      if (!file) return;
      const defaultTitle = file.name.replace(/\.[^.]+$/, "") || "Guitar_Tab";
      runExtraction(() => {
        const form = new FormData();
        form.append("file", file);
        return fetch(`${API_URL}/extract-file`, { method: "POST", body: form });
      }, defaultTitle);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      setPanels((prev) => {
        const oldIdx = prev.findIndex((p) => p.id === active.id);
        const newIdx = prev.findIndex((p) => p.id === over.id);
        return arrayMove(prev, oldIdx, newIdx);
      });
    }
  };

  const handleDelete = useCallback((id: string) => {
    setPanels((prev) => prev.filter((p) => p.id !== id));
  }, []);

  const handleDownloadPDF = async () => {
    if (!panels.length) return;
    setPdfLoading(true);
    try {
      const res = await fetch(`${API_URL}/generate-pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ panels, title: title || "Guitar_Tab" }),
      });
      if (!res.ok) throw new Error("PDF generation failed");
      const blob = await res.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `${title || "Guitar_Tab"}.pdf`;
      link.click();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setPdfLoading(false);
    }
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--paper)" }}>
      {/* Header */}
      <header
        className="border-b border-black/10 px-6 py-4 flex items-center justify-between"
        style={{ background: "var(--tab)" }}
      >
        <div className="flex items-center gap-3">
          <span className="font-mono font-semibold text-lg tracking-tight" style={{ color: "var(--accent)" }}>
            GetTabs - Kenneth Acoustic
          </span>
          <span className="text-xs px-2 py-0.5 rounded" style={{ background: "#ffffff15", color: "#aaa" }}>
            beta
          </span>
        </div>
        {panels.length > 0 && (
          <div className="flex items-center gap-3">
            <span className="text-sm" style={{ color: "#888" }}>
              {panels.length} panel{panels.length !== 1 ? "s" : ""}
            </span>
            <button
              onClick={handleDownloadPDF}
              disabled={pdfLoading}
              className="font-mono text-sm font-medium px-4 py-1.5 rounded transition-opacity"
              style={{ background: "var(--accent)", color: "var(--ink)", opacity: pdfLoading ? 0.6 : 1 }}
            >
              {pdfLoading ? "Building PDF..." : "↓ Download PDF"}
            </button>
          </div>
        )}
      </header>

      {/* Input area */}
      <div className="max-w-3xl mx-auto px-6 pt-10 pb-6">
        {/* Mode toggle */}
        <div className="flex mb-4 rounded overflow-hidden border" style={{ borderColor: "#ddd", width: "fit-content" }}>
          {(["url", "file"] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className="font-mono text-xs px-4 py-1.5 transition-colors"
              style={{
                background: mode === m ? "var(--ink)" : "#fff",
                color: mode === m ? "#fff" : "var(--muted)",
              }}
            >
              {m === "url" ? "YouTube URL (only works locally)" : "Upload File"}
            </button>
          ))}
        </div>

        {mode === "url" ? (
          <>
            <div className="mb-2">
              <label className="font-mono text-xs tracking-widest uppercase" style={{ color: "var(--muted)" }}>
                YouTube URL
              </label>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && canExtract && handleExtract()}
                placeholder="https://www.youtube.com/watch?v=..."
                className="flex-1 font-mono text-sm px-4 py-3 rounded border outline-none"
                style={{ background: "#fff", border: "1.5px solid #ddd", color: "var(--ink)" }}
              />
              <button
                onClick={handleExtract}
                disabled={!canExtract}
                className="font-mono text-sm font-semibold px-6 py-3 rounded transition-all"
                style={{
                  background: !canExtract ? "#ccc" : "var(--ink)",
                  color: "#fff",
                  cursor: !canExtract ? "not-allowed" : "pointer",
                }}
              >
                {status === "loading" ? "Working..." : "Extract"}
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="flex gap-2 items-stretch">
              <label
                className="flex-1 flex flex-col items-center justify-center gap-1 rounded border-2 border-dashed cursor-pointer py-6 transition-colors"
                style={{
                  borderColor: file ? "var(--ink)" : "#ccc",
                  background: file ? "#f9f9f7" : "#fff",
                }}
              >
                <input
                  type="file"
                  accept="video/*"
                  className="hidden"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
                <span className="font-mono text-sm" style={{ color: file ? "var(--ink)" : "#aaa" }}>
                  {file ? file.name : "Click to choose a video file"}
                </span>
                {!file && (
                  <span className="text-xs" style={{ color: "#bbb" }}>mp4, mov, webm…</span>
                )}
              </label>
              <button
                onClick={handleExtract}
                disabled={!canExtract}
                className="font-mono text-sm font-semibold px-6 rounded transition-all"
                style={{
                  background: !canExtract ? "#ccc" : "var(--ink)",
                  color: "#fff",
                  cursor: !canExtract ? "not-allowed" : "pointer",
                }}
              >
                {status === "loading" ? "Working..." : "Extract"}
              </button>
            </div>
          </>
        )}

        {/* Title input — shown after extraction */}
        {status === "done" && (
          <div className="mt-3 flex items-center gap-2">
            <label className="font-mono text-xs tracking-widest uppercase whitespace-nowrap" style={{ color: "var(--muted)" }}>
              PDF Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="flex-1 font-mono text-sm px-3 py-1.5 rounded border outline-none"
              style={{ background: "#fff", border: "1.5px solid #ddd", color: "var(--ink)" }}
            />
          </div>
        )}
      </div>

      {/* States */}
      {status === "loading" && (
        <div className="max-w-3xl mx-auto px-6 py-12 text-center">
          <div className="inline-flex flex-col items-center gap-4">
            <div
              className="w-10 h-10 rounded-full border-2 animate-spin"
              style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
            />
            <p className="font-mono text-sm" style={{ color: "var(--muted)" }}>
              {progress}
            </p>
            <p className="text-xs" style={{ color: "#bbb" }}>
              This takes 1–3 minutes depending on video length
            </p>
          </div>
        </div>
      )}

      {status === "error" && (
        <div className="max-w-3xl mx-auto px-6">
          <div className="rounded p-4 border" style={{ background: "#fff0f0", borderColor: "#f5c6c6" }}>
            <p className="font-mono text-sm" style={{ color: "var(--danger)" }}>
              Error: {error}
            </p>
          </div>
        </div>
      )}

      {status === "idle" && (
        <div className="max-w-3xl mx-auto px-6 py-12 text-center">
          <p className="font-mono text-sm" style={{ color: "var(--muted)" }}>
            {mode === "url"
              ? "Paste a YouTube guitar tutorial URL and hit Extract."
              : "Upload a local video file and hit Extract."}
          </p>
          <p className="text-xs mt-2" style={{ color: "#bbb" }}>
            Works with tutorials that show a scrolling tab overlay at the bottom.
          </p>
        </div>
      )}

      {/* Panel editor */}
      {status === "done" && panels.length > 0 && (
        <div className="max-w-4xl mx-auto px-6 pb-16">
          <div className="flex items-center justify-between mb-4">
            <p className="font-mono text-xs tracking-widest uppercase" style={{ color: "var(--muted)" }}>
              Drag to reorder · Click × to remove · Note: last measure of each panel overlaps with next
            </p>
          </div>

          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={panels.map((p) => p.id)} strategy={verticalListSortingStrategy}>
              <div className="flex flex-col gap-3">
                {panels.map((panel, idx) => (
                  <SortablePanel
                    key={panel.id}
                    panel={panel}
                    index={idx}
                    onDelete={handleDelete}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>

          <div className="mt-8 flex justify-center">
            <button
              onClick={handleDownloadPDF}
              disabled={pdfLoading}
              className="font-mono text-sm font-semibold px-8 py-3 rounded-full transition-all"
              style={{
                background: "var(--ink)",
                color: "#fff",
                opacity: pdfLoading ? 0.6 : 1,
              }}
            >
              {pdfLoading ? "Building PDF..." : `↓ Download PDF (${panels.length} panels)`}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
