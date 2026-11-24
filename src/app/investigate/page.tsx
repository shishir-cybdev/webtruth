"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import { Search, Zap, AlertTriangle, CheckCircle, Loader2, Clock, Shield, FileSearch, BarChart3, ChevronRight, Info } from "lucide-react";
import Link from "next/link";
import { INVESTIGATION_STEPS } from "@/data";
import type { InvestigationStep } from "@/types";

function DemoModeBanner() {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-3 glass border border-amber-500/30 rounded-xl px-5 py-3.5 text-sm mb-8"
    >
      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
      <div>
        <span className="text-amber-400 font-semibold">DEMO MODE</span>
        <span className="text-slate-400 ml-2">
          This is a simulated investigation workflow. No live data is fetched. Real MCP intelligence agents launch in Phase 2.
        </span>
      </div>
    </motion.div>
  );
}

function StepIcon({ status }: { status: InvestigationStep["status"] }) {
  if (status === "complete") return <CheckCircle className="w-5 h-5 text-cyan-400" />;
  if (status === "running") return <Loader2 className="w-5 h-5 text-violet-400 animate-spin" />;
  if (status === "error") return <AlertTriangle className="w-5 h-5 text-red-400" />;
  return <Clock className="w-5 h-5 text-slate-600" />;
}

function InvestigationPipeline({ steps }: {
  steps: InvestigationStep[];
}) {
  return (
    <div className="space-y-3">
      {steps.map((step, i) => (
        <motion.div
          key={step.id}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.08, duration: 0.4 }}
          className={`flex items-start gap-4 p-4 rounded-xl border transition-all duration-300 ${
            step.status === "complete"
              ? "glass border-cyan-500/20 bg-cyan-500/5"
              : step.status === "running"
              ? "glass border-violet-500/30 bg-violet-500/5"
              : step.status === "error"
              ? "glass border-red-500/20 bg-red-500/5"
              : "border-slate-800/50 bg-slate-900/30"
          }`}
        >
          <div className="mt-0.5 shrink-0">
            <StepIcon status={step.status} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-1">
              <span className={`text-sm font-semibold ${
                step.status === "complete" ? "text-cyan-400" :
                step.status === "running" ? "text-violet-400" :
                step.status === "error" ? "text-red-400" : "text-slate-500"
              }`}>
                {step.label}
              </span>
              {step.status === "running" && (
                <span className="text-xs glass border border-violet-500/20 text-violet-400 px-2 py-0.5 rounded-full animate-pulse">
                  Running
                </span>
              )}
              {step.status === "complete" && step.durationMs && (
                <span className="text-xs text-slate-600">{step.durationMs}ms</span>
              )}
            </div>
            <p className="text-xs text-slate-500">{step.description}</p>
            <div className="flex items-center gap-1.5 mt-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-slate-600" />
              <span className="text-xs text-slate-600 font-mono">{step.mcpServer}</span>
            </div>
          </div>
          {step.status === "running" && (
            <div className="shrink-0">
              <div className="w-24 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-violet-500 to-cyan-400 rounded-full"
                  initial={{ width: "0%" }}
                  animate={{ width: "70%" }}
                  transition={{ duration: 2, ease: "easeOut" }}
                />
              </div>
            </div>
          )}
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
      transition={{ duration: 0.6 }}
      className="glass rounded-2xl border border-cyan-500/20 p-6 mt-8"
    >
      {/* Demo label */}
      <div className="flex items-center gap-2 mb-6 pb-4 border-b border-slate-800">
        <Info className="w-4 h-4 text-amber-400" />
        <span className="text-xs text-amber-400 font-medium">SIMULATED RESULTS — Not real data</span>
      </div>

      <div className="flex items-start gap-4 mb-6">
        <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center shrink-0">
          <FileSearch className="w-6 h-6 text-cyan-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-slate-100 mb-1">
            Investigation: &quot;{query}&quot;
          </h3>
          <p className="text-sm text-slate-500">
            In Phase 2, this would display live intelligence results from 6 MCP servers.
          </p>
        </div>
      </div>

      {/* Fake result tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        {[
          { label: "Price Range Found", value: "₹1,30,000 – ₹1,95,000", icon: BarChart3, color: "cyan", note: "Illustrative range" },
          { label: "Trust Score", value: "72 / 100", icon: Shield, color: "violet", note: "Simulated score" },
          { label: "Contradictions", value: "3 Flagged", icon: AlertTriangle, color: "amber", note: "Demo flags" },
        ].map(({ label, value, icon: Icon, color, note }) => (
          <div key={label} className={`glass rounded-xl border p-4 ${
            color === "cyan" ? "border-cyan-500/15" :
            color === "violet" ? "border-violet-500/15" : "border-amber-500/15"
          }`}>
            <Icon className={`w-4 h-4 mb-2 ${
              color === "cyan" ? "text-cyan-400" :
              color === "violet" ? "text-violet-400" : "text-amber-400"
            }`} />
            <div className="text-xs text-slate-500 mb-1">{label}</div>
            <div className={`text-lg font-bold ${
              color === "cyan" ? "text-cyan-400" :
              color === "violet" ? "text-violet-400" : "text-amber-400"
            }`}>{value}</div>
            <div className="text-xs text-slate-700 mt-1">{note}</div>
          </div>
        ))}
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <Link
          href="/compare"
          className="flex items-center justify-center gap-2 px-5 py-3 text-sm font-semibold rounded-xl bg-gradient-to-r from-cyan-400 to-cyan-500 hover:shadow-lg hover:shadow-cyan-500/25 transition-all hover:scale-105"
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

function InvestigateContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialQuery = searchParams.get("q") || "";

  const [query, setQuery] = useState(initialQuery);
  const [inputValue, setInputValue] = useState(initialQuery);
  const [steps, setSteps] = useState<InvestigationStep[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    if (initialQuery) {
      startInvestigation(initialQuery);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function startInvestigation(q: string) {
    setQuery(q);
    setIsComplete(false);
    setIsRunning(true);

    const initialSteps: InvestigationStep[] = INVESTIGATION_STEPS.map((s) => ({
      ...s,
      status: "pending",
    }));
    setSteps(initialSteps);

    let stepIdx = 0;
    const durations = [600, 1200, 1800, 1000, 900, 700];

    function runNext() {
      if (stepIdx >= INVESTIGATION_STEPS.length) {
        setIsRunning(false);
        setIsComplete(true);
        return;
      }
      setSteps((prev) =>
        prev.map((s, i) => i === stepIdx ? { ...s, status: "running" } : s)
      );

      const dur = durations[stepIdx] ?? 1000;
      setTimeout(() => {
        setSteps((prev) =>
          prev.map((s, i) =>
            i === stepIdx ? { ...s, status: "complete", durationMs: dur } : s
          )
        );
        stepIdx++;
        setTimeout(runNext, 200);
      }, dur);
    }

    runNext();
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!inputValue.trim()) return;
    router.replace(`/investigate?q=${encodeURIComponent(inputValue.trim())}`);
    startInvestigation(inputValue.trim());
  }

  return (
    <div className="min-h-screen pt-24 pb-16 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-8"
        >
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-3">
            <Link href="/" className="hover:text-slate-300 transition-colors">Home</Link>
            <ChevronRight className="w-3 h-3" />
            <span className="text-cyan-400">Investigate</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-100 mb-2">
            Product Investigation
          </h1>
          <p className="text-slate-400">AI-powered multi-source analysis · <span className="text-amber-400 font-medium">Demo Mode</span></p>
        </motion.div>

        <DemoModeBanner />

        {/* Search form */}
        <motion.form
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5 }}
          onSubmit={handleSubmit}
          className="mb-8"
        >
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder='e.g. "MacBook Pro 14 M3" or "Sony WH-1000XM5"'
                className="w-full glass border border-slate-700/50 rounded-xl pl-11 pr-4 py-4 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500/40 transition-colors text-sm"
                aria-label="Product to investigate"
              />
            </div>
            <button
              type="submit"
              disabled={isRunning || !inputValue.trim()}
              className="flex items-center gap-2 px-6 py-4 text-sm font-semibold rounded-xl bg-gradient-to-r from-cyan-400 to-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-lg hover:shadow-cyan-500/25 transition-all hover:scale-105 active:scale-95"
              style={{ color: "#020817" }}
            >
              {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              {isRunning ? "Running…" : "Investigate"}
            </button>
          </div>
        </motion.form>

        {/* Pipeline */}
        <AnimatePresence>
          {steps.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="mb-8"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="text-sm font-semibold text-slate-300">MCP Investigation Pipeline</div>
                {isRunning && (
                  <span className="text-xs glass border border-violet-500/20 text-violet-400 px-2.5 py-1 rounded-full animate-pulse">
                    Live
                  </span>
                )}
                {isComplete && (
                  <span className="text-xs glass border border-green-500/20 text-green-400 px-2.5 py-1 rounded-full">
                    Complete
                  </span>
                )}
              </div>
              <InvestigationPipeline steps={steps} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Results */}
        <AnimatePresence>
          {isComplete && query && (
            <SimulatedResultCard query={query} />
          )}
        </AnimatePresence>

        {/* Empty state */}
        {steps.length === 0 && !isComplete && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="text-center py-20"
          >
            <div className="w-20 h-20 rounded-2xl glass border border-cyan-500/15 flex items-center justify-center mx-auto mb-6">
              <FileSearch className="w-9 h-9 text-cyan-500/50" />
            </div>
            <h2 className="text-xl font-semibold text-slate-400 mb-2">Enter a product to investigate</h2>
            <p className="text-sm text-slate-600 max-w-sm mx-auto">
              Type any product name or model number above. The simulated investigation pipeline will walk through each MCP server stage.
            </p>
          </motion.div>
        )}
      </div>
    </div>
  );
}

export default function InvestigatePage() {
  return (
    <Suspense fallback={<div className="min-h-screen pt-24 flex items-center justify-center"><Loader2 className="w-8 h-8 text-cyan-400 animate-spin" /></div>}>
      <InvestigateContent />
    </Suspense>
  );
}
