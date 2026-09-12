import React, { useState, useRef } from "react";
import { UploadCloud, Loader2, CheckCircle2, AlertTriangle } from "lucide-react";
import { parseLetterboxdFile } from "./parser";
import { apiClient } from "../../services/api";
import type { ImportResponse } from "../../types/api";

interface UploadZoneProps {
  onImportSuccess: (data: ImportResponse) => void;
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onImportSuccess }) => {
  const [username, setUsername] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (file: File) => {
    if (!username.trim()) {
      setErrorMessage("Please enter your Letterboxd username first.");
      return;
    }

    setErrorMessage(null);
    setIsProcessing(true);
    setStatusMessage("Extracting and parsing CSV records locally...");

    try {
      const { entries } = await parseLetterboxdFile(file);
      setStatusMessage(`Submitting ${entries.length} records to backend...`);

      const response = await apiClient.post<ImportResponse>(
        "/api/v1/imports/letterboxd",
        {
          username: username.trim(),
          entries,
        }
      );

      setStatusMessage("Import complete!");
      onImportSuccess(response.data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to parse and upload file.";
      setErrorMessage(msg);
    } finally {
      setIsProcessing(false);
    }
  };

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto space-y-4">
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
          Letterboxd Username
        </label>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="e.g. pak47"
          disabled={isProcessing}
          className="w-full bg-surface border border-border-zinc rounded-lg px-4 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-accent"
        />
      </div>

      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          isProcessing
            ? "border-zinc-700 bg-surface/50 cursor-not-allowed"
            : "border-zinc-700 hover:border-accent hover:bg-surface/80 bg-surface"
        }`}
      >
        <input
          type="file"
          ref={fileInputRef}
          accept=".zip,.csv"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
        />

        <div className="flex flex-col items-center justify-center space-y-3">
          {isProcessing ? (
            <Loader2 className="w-10 h-10 text-accent animate-spin" />
          ) : (
            <UploadCloud className="w-10 h-10 text-zinc-400 group-hover:text-accent" />
          )}

          <div>
            <p className="font-medium text-zinc-200">
              {isProcessing ? "Processing dataset..." : "Drop letterboxd-export.zip or diary.csv"}
            </p>
            <p className="text-xs text-zinc-400 mt-1">
              Decompressed and parsed directly in your browser.
            </p>
          </div>

          {statusMessage && (
            <div className="flex items-center gap-2 text-xs text-accent bg-accent/10 py-1.5 px-3 rounded-md border border-accent/20">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>{statusMessage}</span>
            </div>
          )}

          {errorMessage && (
            <div className="flex items-center gap-2 text-xs text-rose-400 bg-rose-950/20 py-1.5 px-3 rounded-md border border-rose-900/50">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>{errorMessage}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};