"use client";

import { useState, useEffect, useRef, Suspense, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { motion } from "motion/react";
import {
  Search,
  Zap,
  AlertTriangle,
  CheckCircle,
  Loader2,
  Clock,
  Shield,
  FileSearch,
  BarChart3,
  ChevronRight,
  Info,
  RefreshCw,
  Radio,
  Server,
} from "lucide-react";
import Link from "next/link";
import { INVESTIGATION_STEPS } from "@/data";
import type { InvestigationStep } from "@/types";
import type {
  BackendStepStatus,
  InvestigationResponse,
  InvestigationSSEEvent,
  MCPHealthResponse,
  PipelineStepInfo,
} from "@/types/api";
import {
  ApiError,
  checkBackendHealth,
  checkMcpHealth,
  createInvestigation,
  getInvestigation,
  subscribeToInvestigationEvents,
} from "@/lib/api";
import { MCPPipeline3DWrapper } from "@/components/MCPPipeline3DWrapper";
import type { MCPNodeState } from "@/components/MCPPipeline3D";
import { InvestigationResultsDashboard } from "@/components/InvestigationResultsDashboard";

function DemoModeBanner() {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-3 glass border border-amber-500/30 rounded-xl px-5 py-3.5 text-sm mb-6"
    >
      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
      <div>
        <span className="text-amber-400 font-semibold">DEMO MODE</span>
        <span className="text-slate-400 ml-2">
          Simulated workflow only — no real MCP tools are executed. Switch to Live MCP Mode to run the real FastAPI + stdio MCP pipeline.
        </span>
      </div>
    </motion.div>
  );
}

function StepIcon({ status }: { status: BackendStepStatus | InvestigationStep["status"] }) {
  if (status === "complete" || status === "completed") {
    return <CheckCircle className="w-5 h-5 text-green-400" />;
  }
  if (status === "running") {
    return <Loader2 className="w-5 h-5 text-violet-400 animate-spin" />;
  }
  if (status === "error" || status === "failed") {
    return <AlertTriangle className="w-5 h-5 text-red-400" />;
  }
  return <Clock className="w-5 h-5 text-slate-600" />;
}

function RealPipelineList({ steps }: { steps: PipelineStepInfo[] }) {
  return (
    <div className="space-y-3">
      {steps.map((step, i) => (
        <motion.div
          key={step.step_id}
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.05, duration: 0.35 }}
          className={`flex items-start gap-4 p-4 rounded-xl border transition-all duration-300 ${
            step.status === "completed"
              ? "glass border-green-500/25 bg-green-500/5"
              : step.status === "running"
              ? "glass border-violet-500/35 bg-violet-500/10"
              : step.status === "failed"
              ? "glass border-red-500/30 bg-red-500/5"
              : "border-slate-800/50 bg-slate-900/30"
          }`}
        >
          <div className="mt-0.5 shrink-0">
            <StepIcon status={step.status} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-1 flex-wrap">
              <span
                className={`text-sm font-semibold ${
                  step.status === "completed"
                    ? "text-green-400"
                    : step.status === "running"
                    ? "text-violet-300"
                    : step.status === "failed"
                    ? "text-red-400"
                    : "text-slate-400"
                }`}
              >
                {step.label}
              </span>
              {step.status === "running" && (
                <span className="text-[11px] font-mono glass border border-violet-500/30 text-violet-300 px-2 py-0.5 rounded-full animate-pulse">
                  Running
                </span>
              )}
              {step.status === "completed" && (
                <span className="text-[11px] font-mono text-green-400/80">Completed</span>
              )}
              {step.status === "failed" && (
                <span className="text-[11px] font-mono text-red-400">Failed</span>
              )}
            </div>
            <p className="text-xs text-slate-400">{step.message || step.description}</p>
            <div className="flex items-center gap-1.5 mt-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-cyan-500/70" />
              <span className="text-[11px] text-slate-500 font-mono">{step.mcp_server}</span>
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

function DemoPipelineList({ steps }: { steps: InvestigationStep[] }) {
  return (
    <div className="space-y-3">
      {steps.map((step, i) => (
        <motion.div
          key={step.id}
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.06, duration: 0.35 }}
          className={`flex items-start gap-4 p-4 rounded-xl border transition-all duration-300 ${
            step.status === "complete"
              ? "glass border-cyan-500/20 bg-cyan-500/5"
              : step.status === "running"
              ? "glass border-violet-500/30 bg-violet-500/5"
              : "border-slate-800/50 bg-slate-900/30"
          }`}
        >
          <div className="mt-0.5 shrink-0">
            <StepIcon status={step.status} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-1">
              <span
                className={`text-sm font-semibold ${
                  step.status === "complete"
                    ? "text-cyan-400"
                    : step.status === "running"
                    ? "text-violet-400"
                    : "text-slate-500"
                }`}
              >
                {step.label}
              </span>
            </div>
            <p className="text-xs text-slate-500">{step.description}</p>
            <div className="flex items-center gap-1.5 mt-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-slate-600" />
              <span className="text-xs text-slate-600 font-mono">{step.mcpServer}</span>
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

function SimulatedResultCard({ query }: { query: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="glass rounded-2xl border border-amber-500/25 p-6 mt-8"
    >
      <div className="flex items-center gap-2 mb-6 pb-4 border-b border-slate-800">
        <Info className="w-4 h-4 text-amber-400" />
        <span className="text-xs text-amber-400 font-medium">
          SIMULATED DEMO RESULTS — Not real data
        </span>
      </div>

      <div className="flex items-start gap-4 mb-6">
        <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center shrink-0">
          <FileSearch className="w-6 h-6 text-cyan-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-slate-100 mb-1">
            Demo Investigation: &quot;{query}&quot;
          </h3>
          <p className="text-sm text-slate-500">
            Switch to Live MCP Mode above to run real Browser, Evidence, Comparison, and Trust MCP servers.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        {[
          { label: "Price Range Found", value: "₹1,30,000 – ₹1,95,000", icon: BarChart3, color: "cyan", note: "Illustrative demo range" },
          { label: "Demo Indicator", value: "72 / 100", icon: Shield, color: "violet", note: "Simulated score" },
          { label: "Contradictions", value: "3 Flagged", icon: AlertTriangle, color: "amber", note: "Demo flags" },
        ].map(({ label, value, icon: Icon, color, note }) => (
          <div
            key={label}
            className={`glass rounded-xl border p-4 ${
              color === "cyan"
                ? "border-cyan-500/15"
                : color === "violet"
                ? "border-violet-500/15"
                : "border-amber-500/15"
            }`}
          >
            <Icon
              className={`w-4 h-4 mb-2 ${
                color === "cyan"
                  ? "text-cyan-400"
                  : color === "violet"
                  ? "text-violet-400"
                  : "text-amber-400"
              }`}
            />
            <div className="text-xs text-slate-500 mb-1">{label}</div>
            <div
              className={`text-lg font-bold ${
                color === "cyan"
                  ? "text-cyan-400"
                  : color === "violet"
                  ? "text-violet-400"
                  : "text-amber-400"
              }`}
            >
              {value}
            </div>
            <div className="text-xs text-slate-600 mt-1">{note}</div>
          </div>
        ))}
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <Link
          href="/compare"
          className="flex items-center justify-center gap-2 px-5 py-3 text-sm font-semibold rounded-xl bg-gradient-to-r from-cyan-400 to-cyan-500 hover:shadow-lg hover:shadow-cyan-500/25 transition-all"
          style={{ color: "#020817" }}
        >
          Compare Products
          <ChevronRight className="w-4 h-4" />
        </Link>
        <Link
          href="/evidence"
          className="flex items-center justify-center gap-2 px-5 py-3 text-sm font-semibold rounded-xl glass border border-violet-500/20 text-violet-400 hover:border-violet-400/40 transition-all"
        >
          View Evidence
          <ChevronRight className="w-4 h-4" />
        </Link>
      </div>
    </motion.div>
  );
}

function extractNodeStates(steps: PipelineStepInfo[]): MCPNodeState {
  const getStatus = (id: string): BackendStepStatus =>
    steps.find((s) => s.step_id === id)?.status ?? "pending";

  return {
    browser: getStatus("step-browser"),
    evidence: getStatus("step-evidence"),
    comparison: getStatus("step-comparison"),
    trust: getStatus("step-trust"),
  };
}

function InvestigateContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const initialQuery = searchParams.get("q") || "";
  const initialCategory = searchParams.get("category") || "";
  const initialBudget = searchParams.get("budget") || "";
  const initialUrls = searchParams.get("urls") || "";
  const initialMode = searchParams.get("mode") === "demo" ? "demo" : "real";

  const [inputValue, setInputValue] = useState(initialQuery);
  const [category, setCategory] = useState(initialCategory);
  const [budgetInr, setBudgetInr] = useState(initialBudget);
  const [targetUrlsInput, setTargetUrlsInput] = useState(initialUrls);
  const [mode, setMode] = useState<"real" | "demo">(initialMode);
  const [showAdvanced, setShowAdvanced] = useState(Boolean(initialBudget || initialUrls));

  // Backend health state
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [mcpHealth, setMcpHealth] = useState<MCPHealthResponse | null>(null);

  // Real investigation state
  const [activeQuery, setActiveQuery] = useState(initialQuery);
  const [realInvestigation, setRealInvestigation] = useState<InvestigationResponse | null>(null);
  const [timelineEvents, setTimelineEvents] = useState<InvestigationSSEEvent[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Demo mode state
  const [demoSteps, setDemoSteps] = useState<InvestigationStep[]>([]);
  const [demoComplete, setDemoComplete] = useState(false);

  const cleanupRef = useRef<(() => void) | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopStreams = useCallback(() => {
    if (cleanupRef.current) {
      cleanupRef.current();
      cleanupRef.current = null;
    }
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => stopStreams();
  }, [stopStreams]);

  // Check backend & MCP health on mount
  useEffect(() => {
    let mounted = true;
    checkBackendHealth()
      .then(() => {
        if (!mounted) return;
        setBackendStatus("online");
        checkMcpHealth()
          .then((h) => {
            if (mounted) setMcpHealth(h);
          })
          .catch(() => {
            // MCP audit optional
          });
      })
      .catch(() => {
        if (mounted) setBackendStatus("offline");
      });
    return () => {
      mounted = false;
    };
  }, []);

  const startDemoInvestigation = useCallback((q: string) => {
    stopStreams();
    setActiveQuery(q);
    setErrorMsg(null);
    setRealInvestigation(null);
    setDemoComplete(false);
    setIsRunning(true);

    const initialSteps: InvestigationStep[] = INVESTIGATION_STEPS.map((s) => ({
      ...s,
      status: "pending",
    }));
    setDemoSteps(initialSteps);

    let stepIdx = 0;
    const durations = [500, 900, 1100, 800, 700, 500];

    function runNext() {
      if (stepIdx >= INVESTIGATION_STEPS.length) {
        setIsRunning(false);
        setDemoComplete(true);
        return;
      }
      setDemoSteps((prev) =>
        prev.map((s, i) => (i === stepIdx ? { ...s, status: "running" } : s))
      );
      const dur = durations[stepIdx] ?? 800;
      setTimeout(() => {
        setDemoSteps((prev) =>
          prev.map((s, i) =>
            i === stepIdx ? { ...s, status: "complete", durationMs: dur } : s
          )
        );
        stepIdx++;
        setTimeout(runNext, 150);
      }, dur);
    }

    runNext();
  }, [stopStreams]);

  const startPollingFallback = useCallback(
    (investigationId: string) => {
      if (pollTimerRef.current) return;
      pollTimerRef.current = setInterval(async () => {
        try {
          const latest = await getInvestigation(investigationId);
          setRealInvestigation(latest);
          if (latest.status === "completed" || latest.status === "failed") {
            stopStreams();
            setIsRunning(false);
            if (latest.status === "failed") {
              setErrorMsg(
                latest.summary || "Investigation failed during MCP pipeline execution."
              );
            }
          }
        } catch (err) {
          // Keep polling unless unrecoverable
          if (err instanceof ApiError && err.status === 404) {
            stopStreams();
            setIsRunning(false);
            setErrorMsg(err.detail);
          }
        }
      }, 2000);
    },
    [stopStreams]
  );

  const startRealInvestigation = useCallback(
    async (q: string, cat: string, budgetStr: string, urlsStr: string) => {
      stopStreams();
      setActiveQuery(q);
      setErrorMsg(null);
      setDemoComplete(false);
      setDemoSteps([]);
      setTimelineEvents([]);
      setRealInvestigation(null);
      setIsRunning(true);

      const parsedUrls = urlsStr
        .split(/[\n,]+/)
        .map((u) => u.trim())
        .filter(Boolean);

      const parsedBudget =
        budgetStr.trim() && !Number.isNaN(Number(budgetStr))
          ? Number(budgetStr)
          : undefined;

      try {
        const created = await createInvestigation({
          query: q,
          category: cat || undefined,
          budget_inr: parsedBudget,
          target_urls: parsedUrls.length > 0 ? parsedUrls : undefined,
          mode: "real",
        });

        setBackendStatus("online");
        setRealInvestigation(created);

        if (created.status === "completed" || created.status === "failed") {
          setIsRunning(false);
          return;
        }

        // Subscribe to live SSE events
        const closeSse = subscribeToInvestigationEvents(created.id, {
          onEvent: async (evt) => {
            setTimelineEvents((prev) => [...prev, evt]);

            // Refresh structured investigation state on stage transitions
            if (
              evt.event_type === "stage_started" ||
              evt.event_type === "stage_completed"
            ) {
              setRealInvestigation((prev) => {
                if (!prev) return prev;
                const updatedSteps = prev.pipeline_steps.map((st) => {
                  if (st.step_id === `step-${evt.stage}`) {
                    return {
                      ...st,
                      status: (evt.status as BackendStepStatus) || st.status,
                      message: evt.message || st.message,
                    };
                  }
                  return st;
                });
                return { ...prev, pipeline_steps: updatedSteps };
              });
            }

            if (evt.event_type === "completed" || evt.event_type === "error") {
              stopStreams();
              try {
                const finalState = await getInvestigation(created.id);
                setRealInvestigation(finalState);
                if (finalState.status === "failed") {
                  setErrorMsg(evt.message || "Investigation failed.");
                }
              } catch {
                // fallback if final fetch fails
              } finally {
                setIsRunning(false);
              }
            }
          },
          onError: () => {
            // Switch to polling fallback if SSE disconnects
            startPollingFallback(created.id);
          },
        });

        cleanupRef.current = closeSse;
        // Also start gentle polling backup in case investigation finishes before SSE connects
        startPollingFallback(created.id);
      } catch (err) {
        setIsRunning(false);
        if (err instanceof ApiError) {
          if (err.status === 0) setBackendStatus("offline");
          setErrorMsg(err.detail || err.message);
        } else {
          setErrorMsg(err instanceof Error ? err.message : "Failed to start investigation.");
        }
      }
    },
    [startPollingFallback, stopStreams]
  );

  // Auto-trigger if navigated with ?q=...
  useEffect(() => {
    if (initialQuery.trim().length < 2) return;
    const timer = setTimeout(() => {
      if (initialMode === "demo") {
        startDemoInvestigation(initialQuery.trim());
      } else {
        startRealInvestigation(
          initialQuery.trim(),
          initialCategory,
          initialBudget,
          initialUrls
        );
      }
    }, 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = inputValue.trim();
    if (trimmed.length < 2) {
      setErrorMsg("Please enter at least 2 characters for the product query.");
      return;
    }
    if (budgetInr && (Number.isNaN(Number(budgetInr)) || Number(budgetInr) <= 0)) {
      setErrorMsg("Budget in INR must be a positive number.");
      return;
    }

    const params = new URLSearchParams();
    params.set("q", trimmed);
    if (category) params.set("category", category);
    if (budgetInr) params.set("budget", budgetInr);
    if (targetUrlsInput.trim()) params.set("urls", targetUrlsInput.trim());
    params.set("mode", mode);
    router.replace(`/investigate?${params.toString()}`);

    if (mode === "demo") {
      startDemoInvestigation(trimmed);
    } else {
      startRealInvestigation(trimmed, category, budgetInr, targetUrlsInput);
    }
  }

  const nodeStates: MCPNodeState = realInvestigation
    ? extractNodeStates(realInvestigation.pipeline_steps)
    : { browser: "pending", evidence: "pending", comparison: "pending", trust: "pending" };

  return (
    <div className="min-h-screen pt-24 pb-20 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header & Live MCP Status */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="mb-6"
        >
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Link href="/" className="hover:text-slate-300 transition-colors">
                Home
              </Link>
              <span>/</span>
              <span className="text-cyan-400">Investigate</span>
            </div>

            <div className="flex items-center gap-2">
              {backendStatus === "online" ? (
                <span className="inline-flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded-full bg-green-500/10 text-green-400 border border-green-500/25">
                  <Radio className="w-3 h-3 animate-pulse" />
                  FastAPI Online
                  {mcpHealth ? ` • ${mcpHealth.total_tools_count} MCP Tools` : ""}
                </span>
              ) : backendStatus === "offline" ? (
                <span className="inline-flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded-full bg-red-500/10 text-red-400 border border-red-500/25">
                  <Server className="w-3 h-3" />
                  Backend Offline (127.0.0.1:8000)
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Checking Backend…
                </span>
              )}
            </div>
          </div>

          <h1 className="text-3xl sm:text-4xl font-bold text-slate-100 mb-2">
            Product{" "}
            <span className="bg-gradient-to-r from-cyan-400 to-violet-400 bg-clip-text text-transparent">
              Investigation
            </span>
          </h1>
          <p className="text-slate-400 text-sm">
            Multi-stage MCP orchestration across Browser, Evidence, Comparison, and Trust servers.
          </p>
        </motion.div>

        {/* Mode Banner */}
        {mode === "demo" ? (
          <DemoModeBanner />
        ) : (
          <div className="flex items-center gap-3 glass border border-cyan-500/25 rounded-xl px-5 py-3 text-xs mb-6">
            <Shield className="w-4 h-4 text-cyan-400 shrink-0" />
            <div>
              <span className="text-cyan-400 font-semibold font-mono">LIVE MCP ORCHESTRATION</span>
              <span className="text-slate-400 ml-2">
                Connected to real FastAPI engine &amp; stdio MCP subprocesses. No fabricated prices or mock scores.
              </span>
            </div>
          </div>
        )}

        {/* Search & Parameters Form */}
        <form onSubmit={handleSubmit} className="mb-8 space-y-3">
          <div className="relative flex items-center glass rounded-2xl border border-cyan-500/25 focus-within:border-cyan-400/60 transition-colors">
            <Search className="absolute left-4 w-5 h-5 text-cyan-400 pointer-events-none" />
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder='Enter product name or model (e.g. "Dell XPS 15 9530")…'
              className="w-full bg-transparent py-4 pr-36 text-slate-200 placeholder-slate-500 focus:outline-none text-sm"
              style={{ paddingLeft: "3rem" }}
              aria-label="Product investigation query"
            />
            <button
              type="submit"
              disabled={isRunning}
              className="absolute right-2 flex items-center gap-1.5 px-4 py-2.5 text-xs font-semibold rounded-xl bg-gradient-to-r from-cyan-400 to-cyan-500 hover:shadow-lg hover:shadow-cyan-500/25 transition-all disabled:opacity-50"
              style={{ color: "#020817" }}
            >
              {isRunning ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Zap className="w-3.5 h-3.5" />
              )}
              {isRunning ? "Running…" : "Investigate"}
            </button>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-1.5 glass rounded-lg p-1 border border-slate-800">
              <button
                type="button"
                onClick={() => setMode("real")}
                className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                  mode === "real"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Live MCP Mode
              </button>
              <button
                type="button"
                onClick={() => setMode("demo")}
                className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                  mode === "demo"
                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Demo Simulation
              </button>
            </div>

            <button
              type="button"
              onClick={() => setShowAdvanced((v) => !v)}
              className="text-slate-400 hover:text-cyan-400 transition-colors font-mono"
            >
              {showAdvanced ? "− Hide parameters" : "+ Category / Budget / Target URLs"}
            </button>
          </div>

          {showAdvanced && (
            <div className="glass rounded-xl border border-slate-800 p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">
                  Category
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-slate-950/70 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
                >
                  <option value="">Auto-detect</option>
                  <option value="smartphone">Smartphone</option>
                  <option value="laptop">Laptop</option>
                  <option value="headphones">Audio / Headphones</option>
                  <option value="monitor">Monitor</option>
                  <option value="tablet">Tablet</option>
                  <option value="camera">Camera</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">
                  Max Budget (INR)
                </label>
                <input
                  type="number"
                  min="1"
                  placeholder="e.g. 185000"
                  value={budgetInr}
                  onChange={(e) => setBudgetInr(e.target.value)}
                  className="w-full bg-slate-950/70 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500/50"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-[11px] font-mono text-slate-400 mb-1">
                  Target URLs (comma or newline separated — public URLs or file:/// fixtures)
                </label>
                <input
                  type="text"
                  placeholder="e.g. https://dell.com/in/p/xps-15-9530-laptop"
                  value={targetUrlsInput}
                  onChange={(e) => setTargetUrlsInput(e.target.value)}
                  className="w-full bg-slate-950/70 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500/50"
                />
              </div>
            </div>
          )}
        </form>

        {/* Error Banner with Retry */}
        {errorMsg && (
          <div className="mb-6 rounded-xl bg-red-500/10 border border-red-500/30 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-start gap-2.5 text-sm text-red-300">
              <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div>
                <div className="font-semibold">Investigation Error</div>
                <div className="text-xs text-red-300/80 mt-0.5">{errorMsg}</div>
              </div>
            </div>
            <button
              type="button"
              onClick={() =>
                mode === "real" && activeQuery
                  ? startRealInvestigation(activeQuery, category, budgetInr, targetUrlsInput)
                  : activeQuery && startDemoInvestigation(activeQuery)
              }
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-red-500/20 hover:bg-red-500/30 text-red-200 border border-red-500/30 shrink-0"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Retry
            </button>
          </div>
        )}

        {/* Persistent 3D MCP Pipeline Visualization in Live Mode */}
        {mode === "real" && <MCPPipeline3DWrapper nodeStates={nodeStates} />}

        {/* Real Stage Tracker */}
        {mode === "real" && realInvestigation && (
          <div className="space-y-6">

            <div className="glass rounded-2xl border border-slate-800 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-slate-200">
                  Live Investigation Pipeline:{" "}
                  <span className="text-cyan-400">&quot;{realInvestigation.query}&quot;</span>
                </h2>
                <span className="text-xs font-mono text-slate-400">
                  Status:{" "}
                  <span
                    className={
                      realInvestigation.status === "completed"
                        ? "text-green-400"
                        : realInvestigation.status === "failed"
                        ? "text-red-400"
                        : "text-violet-400"
                    }
                  >
                    {realInvestigation.status.toUpperCase()}
                  </span>
                </span>
              </div>

              <RealPipelineList steps={realInvestigation.pipeline_steps} />

              {/* Live SSE Event Timeline */}
              {timelineEvents.length > 0 && (
                <div className="mt-6 pt-4 border-t border-slate-800/80">
                  <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 mb-2">
                    Live SSE Event Stream ({timelineEvents.length})
                  </div>
                  <div className="max-h-36 overflow-y-auto space-y-1 font-mono text-[11px] bg-slate-950/60 rounded-xl p-3 border border-slate-800/80">
                    {timelineEvents.map((ev, i) => (
                      <div key={i} className="text-slate-400">
                        <span className="text-cyan-400">[{ev.event_type}]</span>{" "}
                        {ev.stage ? <span className="text-violet-400">{ev.stage}:</span> : null}{" "}
                        {ev.message || ev.status}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {realInvestigation.status === "completed" && (
              <InvestigationResultsDashboard investigation={realInvestigation} />
            )}
          </div>
        )}

        {/* Demo Mode Pipeline & Simulated Results */}
        {mode === "demo" && demoSteps.length > 0 && (
          <div className="glass rounded-2xl border border-slate-800 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-slate-300">
                Simulated Pipeline:{" "}
                <span className="text-amber-400">&quot;{activeQuery}&quot;</span>
              </h2>
              <span className="text-xs text-slate-500">
                {demoSteps.filter((s) => s.status === "complete").length} / {demoSteps.length} steps
              </span>
            </div>
            <DemoPipelineList steps={demoSteps} />
            {demoComplete && <SimulatedResultCard query={activeQuery} />}
          </div>
        )}

        {/* Empty State */}
        {!realInvestigation && demoSteps.length === 0 && !isRunning && !errorMsg && (
          <div className="text-center py-16 glass rounded-2xl border border-slate-800/60">
            <Search className="w-12 h-12 text-slate-700 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-400 mb-2">
              Enter a product to investigate
            </h3>
            <p className="text-sm text-slate-500 max-w-md mx-auto">
              Search any product above to run the 4-server MCP pipeline, or choose Demo Simulation to preview the UI without a running backend.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function InvestigatePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen pt-28 flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
        </div>
      }
    >
      <InvestigateContent />
    </Suspense>
  );
}
