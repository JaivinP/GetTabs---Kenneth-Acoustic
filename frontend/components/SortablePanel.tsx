"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

type Panel = { id: string; image: string };

interface SortablePanelProps {
  panel: Panel;
  index: number;
  onDelete: (id: string) => void;
}

export function SortablePanel({ panel, index, onDelete }: SortablePanelProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: panel.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.45 : 1,
    zIndex: isDragging ? 999 : undefined,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="panel-card flex items-stretch rounded-lg border overflow-hidden"
      {...attributes}
    >
      {/* Drag handle */}
      <div
        {...listeners}
        className="drag-handle flex items-center justify-center px-3 select-none"
        style={{ background: "#1a1a2e", color: "#555", minWidth: 36 }}
        title="Drag to reorder"
      >
        <DragIcon />
      </div>

      {/* Panel number */}
      <div
        className="flex items-center justify-center px-3 font-mono text-xs font-semibold select-none"
        style={{ background: "#f0ebe0", color: "#8a8070", minWidth: 42, borderRight: "1px solid #e0dbd0" }}
      >
        {index + 1}
      </div>

      {/* Tab image */}
      <div className="flex-1 bg-white" style={{ borderRight: "1px solid #e0dbd0" }}>
        <img
          src={`data:image/png;base64,${panel.image}`}
          alt={`Tab panel ${index + 1}`}
          className="w-full h-auto block"
          style={{ maxHeight: 160, objectFit: "contain", objectPosition: "left" }}
        />
      </div>

      {/* Delete */}
      <button
        onClick={() => onDelete(panel.id)}
        className="flex items-center justify-center px-3 transition-colors"
        style={{ background: "#fff8f8", color: "#c0392b", minWidth: 44 }}
        title="Remove panel"
        onMouseEnter={(e) => (e.currentTarget.style.background = "#ffe0e0")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "#fff8f8")}
      >
        ×
      </button>
    </div>
  );
}

function DragIcon() {
  return (
    <svg width="12" height="16" viewBox="0 0 12 16" fill="none">
      <circle cx="3" cy="3" r="1.5" fill="#888" />
      <circle cx="9" cy="3" r="1.5" fill="#888" />
      <circle cx="3" cy="8" r="1.5" fill="#888" />
      <circle cx="9" cy="8" r="1.5" fill="#888" />
      <circle cx="3" cy="13" r="1.5" fill="#888" />
      <circle cx="9" cy="13" r="1.5" fill="#888" />
    </svg>
  );
}
