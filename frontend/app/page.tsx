"use client";

import { useState } from "react";
import { Navbar } from "./components/Navbar";
import { Footer } from "./components/Footer";
import { UploadStep } from "./components/UploadStep";
import { ConfirmationTicketStep } from "./components/ConfirmationTicketStep";
import { RunConsole } from "./components/console/RunConsole";
import type { RunData } from "./lib/runState";

export default function DashboardPage() {
  const [step, setStep] = useState<1 | 2 | 3>(1);

  const [jobConfig, setJobConfig] = useState<{
    input_file?: string;
    sql_file?: string;
    lineage_file?: string;
    isPreset?: boolean;
  }>({});

  const [data, setData] = useState<RunData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleProceedToTicket = (config: {
    input_file?: string;
    sql_file?: string;
    lineage_file?: string;
    isPreset?: boolean;
  }) => {
    setJobConfig(config);
    setStep(2);
  };

  const handleLaunchPipeline = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = jobConfig.isPreset
        ? {}
        : {
            input_file: jobConfig.input_file,
            sql_file: jobConfig.sql_file,
            lineage_file: jobConfig.lineage_file,
          };

      const apiBase = typeof window === "undefined" ? "http://localhost:8000" : `http://${window.location.hostname}:8000`;
      const res = await fetch(`${apiBase}/api/pipeline/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await res.json();
      if (!res.ok) throw new Error(result.detail ?? "Pipeline execution failed.");
      setData(result as RunData);
      setStep(3);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reach the pipeline backend.");
    } finally {
      setLoading(false);
    }
  };

  if (step === 3 && data) return <RunConsole initial={data} />;

  return (
    <div className="min-h-screen bg-[#FFF4EB] text-[#3D1534] flex flex-col justify-between">
      <Navbar />

      <main className="max-w-[1400px] mx-auto px-4 sm:px-8 py-6 sm:py-10 space-y-6 flex-1 w-full">
        {/* STEP 1: Upload Source Configuration */}
        {step === 1 && <UploadStep onProceedToTicket={handleProceedToTicket} />}

        {/* STEP 2: Confirmation Ticket */}
        {step === 2 && (
          <ConfirmationTicketStep
            config={jobConfig}
            onBack={() => setStep(1)}
            onLaunch={handleLaunchPipeline}
            loading={loading}
          />
        )}

        {error && (
          <div role="alert" className="mx-auto max-w-2xl rounded-2xl border-2 border-rose-400 bg-rose-50 p-5 text-sm text-rose-900 shadow-sm">
            <strong className="font-extrabold flex items-center gap-2 text-rose-800">
              Pipeline Run Error
            </strong>
            <p className="mt-1 font-medium">{error}</p>
            <p className="mt-2 text-xs text-rose-700 font-mono">
              Please ensure the backend FastAPI service is active on port 8000 (`python main.py`).
            </p>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
