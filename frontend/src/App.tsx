import { useState, useEffect } from "react";
import { Film } from "lucide-react";
import { UploadZone } from "./features/upload/UploadZone";
import { DashboardView } from "./features/dashboard/DashboardView";

export default function App() {
  const [hasSession, setHasSession] = useState<boolean>(false);

  // Check if a session already exists in localStorage on startup
  useEffect(() => {
    const session = localStorage.getItem("kinostats_session_id");
    if (session) {
      setHasSession(true);
    }
  }, []);

  const handleReset = () => {
    localStorage.removeItem("kinostats_session_id");
    setHasSession(false);
  };

  return (
    <main className="min-h-screen bg-canvas text-zinc-100 flex flex-col items-center p-6 md:p-12 space-y-8">
      {/* Brand Header */}
      <header className="flex items-center gap-3 w-full max-w-6xl">
        <div className="p-2.5 bg-surface border border-border-zinc rounded-xl text-accent">
          <Film className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">KinoStats</h1>
          <p className="text-xs text-zinc-400">Letterboxd Analytics & Completionist Engine</p>
        </div>
      </header>

      {/* Dynamic View: Upload Zone vs Dashboard */}
      {!hasSession ? (
        <div className="w-full flex justify-center pt-8">
          <UploadZone onImportSuccess={() => setHasSession(true)} />
        </div>
      ) : (
        <DashboardView onReset={handleReset} />
      )}
    </main>
  );
}