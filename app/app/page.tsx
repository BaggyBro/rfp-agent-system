"use client";

import { useCallback, useMemo, useState } from "react";

type PipelineStatus = "idle" | "uploading" | "running" | "completed" | "error";

type PipelineResponse = {
  rfp_id: string;
  status: string;
  final_recommendation?: string | null;
  comparison_report?: any;
  risk_report?: any;
  extracted_requirements?: any;
  matched_products_count?: number;
};

type LogEntry = {
  id: number;
  phase: string;
  message: string;
  ts: string;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default function Home() {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState<PipelineStatus>("idle");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [rfpId, setRfpId] = useState("rfp-ui");
  const [response, setResponse] = useState<PipelineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const addLog = useCallback((phase: string, message: string) => {
    setLogs((prev) => [
      ...prev,
      {
        id: prev.length + 1,
        phase,
        message,
        ts: new Date().toLocaleTimeString(),
      },
    ]);
  }, []);

  const handleFile = (file: File | null) => {
    if (!file) return;
    if (file.type !== "application/pdf") {
      setError("Please upload a PDF file.");
      addLog("Validation", "Rejected non-PDF upload.");
      return;
    }
    setError(null);
    setSelectedFile(file);
    addLog("Upload", `Selected file: ${file.name} (${Math.round(file.size / 1024)} KB)`);
  };

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    handleFile(file ?? null);
  };

  const onDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!dragActive) setDragActive(true);
  };

  const onDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const handleBrowseClick = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "application/pdf";
    input.onchange = (e: Event) => {
      const target = e.target as HTMLInputElement;
      const file = target.files?.[0] ?? null;
      handleFile(file);
    };
    input.click();
  };

  const handleSubmit = async () => {
    if (!selectedFile) {
      setError("Please select a PDF to upload.");
      addLog("Validation", "No file selected when trying to run pipeline.");
      return;
    }

    setStatus("uploading");
    setError(null);
    setResponse(null);
    setLogs([]);

    addLog("Upload", "Uploading PDF to FastAPI /rfp-upload/ endpoint...");

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("rfp_id", rfpId || "rfp-ui");

    try {
      setStatus("running");
      addLog(
        "Pipeline",
        "Pipeline started – sales → technical → pricing → comparison → risk → master.",
      );

      const res = await fetch(`${API_BASE}/rfp-upload/`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(
          `Backend returned ${res.status} ${res.statusText}: ${text}`,
        );
      }

      const data = (await res.json()) as PipelineResponse;
      setResponse(data);
      setStatus("completed");

      addLog(
        "Sales agent",
        "Ingested PDF, cleaned and chunked text, generated abstract, cached chunks.",
      );
      addLog(
        "Technical agent",
        "Extracted requirements and matched candidate SKUs from the catalog.",
      );
      addLog(
        "Pricing agent",
        "Estimated pricing for matched products and built pricing summary.",
      );
      addLog(
        "Comparison agent",
        "Ranked products using composite scores and generated comparison report.",
      );
      addLog(
        "Risk & Compliance",
        "Assessed risk level and checked compliance against key requirements.",
      );
      addLog(
        "Master agent",
        "Aggregated everything into a final recommendation for the RFP.",
      );
    } catch (err: any) {
      console.error(err);
      setStatus("error");
      setError(err.message || "Unexpected error when calling backend.");
      addLog("Error", err.message || "Pipeline execution failed.");
    }
  };

  const statusLabel = useMemo(() => {
    switch (status) {
      case "idle":
        return "Waiting for upload";
      case "uploading":
        return "Uploading PDF";
      case "running":
        return "Pipeline running";
      case "completed":
        return "Pipeline completed";
      case "error":
        return "Error";
      default:
        return "";
    }
  }, [status]);

  return (
    <div className="grid gap-6 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      {/* Left: upload + pipeline status */}
      <section className="space-y-4 rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-950 p-6 shadow-xl shadow-black/60">
        <header className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold tracking-tight">
              RFP upload & pipeline
            </h2>
            <p className="text-xs text-slate-400">
              Drag-and-drop a PDF to send it to the sales agent and run the full
              pipeline.
            </p>
          </div>
          <div className="rounded-full border border-amber-400/40 bg-amber-400/10 px-3 py-1 text-xs font-medium text-amber-200">
            {statusLabel}
          </div>
        </header>

        <div
          className={`mt-3 flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition ${
            dragActive
              ? "border-amber-300 bg-amber-400/10"
              : "border-slate-700 bg-slate-900/50 hover:border-slate-400/80 hover:bg-slate-900"
          }`}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onClick={handleBrowseClick}
        >
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-900 text-amber-300 shadow-lg shadow-amber-500/20">
            <span className="text-2xl">📄</span>
          </div>
          <p className="text-sm font-medium">
            Drag & drop your RFP PDF here, or{" "}
            <span className="text-amber-300 underline underline-offset-4">
              browse
            </span>
          </p>
          <p className="mt-1 text-xs text-slate-400">
            We currently accept a single PDF per run. File is processed
            server-side via FastAPI.
          </p>
          {selectedFile && (
            <p className="mt-3 text-xs text-slate-300">
              Selected:{" "}
              <span className="font-medium">{selectedFile.name}</span>
            </p>
          )}
        </div>

        <div className="mt-4 flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-xs text-slate-300">
          <div className="flex flex-wrap items-center gap-2">
            <label className="text-[11px] uppercase tracking-[0.08em] text-slate-400">
              RFP identifier
            </label>
            <input
              className="flex-1 rounded-full border border-slate-700 bg-slate-900/60 px-3 py-1 text-xs outline-none ring-0 focus:border-amber-300 focus:ring-1 focus:ring-amber-400/60"
              value={rfpId}
              onChange={(e) => setRfpId(e.target.value)}
            />
          </div>

          <button
            onClick={handleSubmit}
            disabled={status === "running" || status === "uploading"}
            className="mt-1 inline-flex items-center justify-center gap-2 rounded-full bg-amber-400 px-4 py-2 text-xs font-semibold text-slate-950 shadow-lg shadow-amber-500/40 transition hover:bg-amber-300 disabled:cursor-not-allowed disabled:bg-slate-500 disabled:text-slate-100 disabled:shadow-none"
          >
            {status === "running" || status === "uploading" ? (
              <>
                <span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-900 border-t-amber-700" />
                Running pipeline…
              </>
            ) : (
              <>Run pipeline</>
            )}
          </button>

          {error && (
            <p className="mt-1 text-xs text-red-400">
              <strong>Error:</strong> {error}
            </p>
          )}
        </div>
      </section>

      {/* Right: live logs */}
      <section className="flex h-[360px] flex-col rounded-2xl border border-slate-800 bg-slate-950/80 p-4">
        <header className="mb-2 flex items-center justify-between gap-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
              Agent activity log
            </p>
            <p className="text-[11px] text-slate-500">
              High-level reasoning trace for the current run.
            </p>
          </div>
          <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[10px] text-slate-300">
            {logs.length} events
          </span>
        </header>

        <div className="scroll-thin mt-1 flex-1 space-y-1 overflow-y-auto rounded-xl bg-slate-950/60 p-2 text-xs">
          {logs.length === 0 && (
            <p className="mt-10 text-center text-[11px] text-slate-500">
              No activity yet. Upload a PDF and run the pipeline to see the
              multi-agent thinking trace here.
            </p>
          )}
          {logs.map((log) => (
            <div
              key={log.id}
              className="flex items-start gap-2 rounded-lg border border-slate-800 bg-slate-900/70 px-2 py-1.5"
            >
              <span className="mt-0.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-emerald-400" />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-slate-200">
                    {log.phase}
                  </span>
                  <span className="text-[10px] text-slate-500">{log.ts}</span>
                </div>
                <p className="text-[11px] text-slate-300">{log.message}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Full-width results */}
      <section className="md:col-span-2 mt-4 space-y-4 rounded-2xl border border-slate-800 bg-slate-950/80 p-6">
        <header className="flex items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold tracking-tight">
              Pipeline output
            </h3>
            <p className="text-xs text-slate-400">
              Final recommendation and structured outputs from all agents.
            </p>
          </div>
          {response && (
            <span className="rounded-full border border-emerald-400/40 bg-emerald-400/10 px-3 py-1 text-[11px] font-medium text-emerald-200">
              Status: {response.status}
            </span>
          )}
        </header>

        {!response && (
          <p className="mt-2 text-xs text-slate-500">
            Once the pipeline completes, you&apos;ll see the AI-generated
            recommendation, risk report, comparison summary, and extracted
            requirements here.
          </p>
        )}

        {response && (
          <div className="grid gap-4 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
            <div className="space-y-4">
              <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4">
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                  Final recommendation
                </h4>
                <div className="prose prose-invert max-w-none text-sm leading-relaxed">
                  {response.final_recommendation ? (
                    <pre className="whitespace-pre-wrap text-xs text-slate-100">
                      {response.final_recommendation}
                    </pre>
                  ) : (
                    <p className="text-xs text-slate-500">
                      No recommendation available.
                    </p>
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4">
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                  Technical requirements
                </h4>
                <pre className="scroll-thin max-h-40 overflow-auto rounded-lg bg-slate-950/60 p-3 text-[11px] text-slate-200">
                  {JSON.stringify(
                    response.extracted_requirements ?? {},
                    null,
                    2,
                  )}
                </pre>
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4">
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                  Risk & compliance
                </h4>
                <pre className="scroll-thin max-h-40 overflow-auto rounded-lg bg-slate-950/60 p-3 text-[11px] text-slate-200">
                  {JSON.stringify(response.risk_report ?? {}, null, 2)}
                </pre>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4">
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                  Comparison & pricing
                </h4>
                <p className="mb-1 text-[11px] text-slate-300">
                  Matched products:{" "}
                  <span className="font-semibold">
                    {response.matched_products_count ?? 0}
                  </span>
                </p>
                <pre className="scroll-thin max-h-40 overflow-auto rounded-lg bg-slate-950/60 p-3 text-[11px] text-slate-200">
                  {JSON.stringify(response.comparison_report ?? {}, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
