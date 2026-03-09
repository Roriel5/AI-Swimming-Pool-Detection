"use client";

import { useRef, useState, useCallback } from "react";

interface UploadPanelProps {
  onFileSelected: (file: File) => void;
  loading: boolean;
}

const ACCEPTED = ".png,.jpg,.jpeg,.tiff,.tif";
const MAX_SIZE = 50 * 1024 * 1024; // 50MB

export default function UploadPanel({ onFileSelected, loading }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleFile = useCallback(
    (file: File) => {
      const ext = file.name.toLowerCase().split(".").pop();
      if (!["png", "jpg", "jpeg", "tiff", "tif"].includes(ext || "")) {
        return;
      }
      if (file.size > MAX_SIZE) {
        return;
      }
      setFileName(file.name);
      onFileSelected(file);
    },
    [onFileSelected]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const onDragLeave = () => setDragOver(false);

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="space-y-3">
      <h3 className="text-[11px] font-semibold text-[#6b7280] uppercase tracking-wider">
        Upload Image
      </h3>

      <div
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        className={`drop-zone border border-dashed rounded-md p-4 text-center cursor-pointer transition-colors ${
          dragOver
            ? "drag-over border-[#3b6fa0] bg-[#e8f0f8]"
            : "border-[#d1d5db] hover:border-[#9ca3af] bg-[#fafbfc]"
        }`}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          onChange={onInputChange}
          className="hidden"
        />
        <svg
          className="mx-auto mb-2 text-[#9ca3af]"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
        <p className="text-[12px] text-[#6b7280]">
          {fileName ? fileName : "Drop satellite image or click to browse"}
        </p>
        <p className="text-[10px] text-[#9ca3af] mt-1">PNG, JPG, TIFF up to 50 MB</p>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-[12px] text-[#6b7280]">
          <div className="w-3 h-3 border-2 border-[#3b6fa0] border-t-transparent rounded-full animate-spin" />
          Processing image...
        </div>
      )}
    </div>
  );
}
