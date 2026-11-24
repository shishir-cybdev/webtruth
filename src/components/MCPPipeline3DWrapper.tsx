"use client";

import dynamic from "next/dynamic";
import { useSyncExternalStore } from "react";
import { Globe, Database, GitCompare, ShieldCheck, CheckCircle2, Loader2, AlertTriangle, Clock } from "lucide-react";
import type { MCPNodeState } from "./MCPPipeline3D";
import type { BackendStepStatus } from "@/types/api";

const MCPPipeline3DLazy = dynamic(
  () => import("./MCPPipeline3D").then((m) => ({ default: m.MCPPipeline3D })),
  { ssr: false, loading: () => <MCPPipelineFallback nodeStates={{ browser: "pending", evidence: "pending", comparison: "pending", trust: "pending" }} /> }
);

let webglSupportedCache: boolean | null = null;
function checkWebGLSupport(): boolean {
  if (webglSupportedCache !== null) return webglSupportedCache;
  if (typeof window === "undefined") return true;
  try {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
    webglSupportedCache = !!gl;
    return webglSupportedCache;
  } catch {
    webglSupportedCache = false;
    return false;
  }
}

function StatusBadge({ status }: { status: BackendStepStatus }) {
  if (status === "completed") {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-green-500/15 text-green-400 border border-green-500/30">
        <CheckCircle2 className="w-3 h-3" /> DONE
      </span>
    );
  }
  if (status === "running") {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300 border border-violet-500/40 animate-pulse">
        <Loader2 className="w-3 h-3 animate-spin" /> ACTIVE
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 border border-red-500/40">
        <AlertTriangle className="w-3 h-3" /> FAILED
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800/70 text-slate-500 border border-slate-700/50">
      <Clock className="w-3 h-3" /> WAITING
    </span>
  );
}

export function MCPPipelineFallback({ nodeStates }: { nodeStates: MCPNodeState }) {
  const nodes = [
    { key: "browser" as const, label: "Browser MCP", sub: "Playwright", icon: Globe, color: "text-cyan-400 border-cyan-500/30" },
    { key: "evidence" as const, label: "Evidence MCP", sub: "SQLite Vault", icon: Database, color: "text-green-400 border-green-500/30" },
    { key: "comparison" as const, label: "Comparison MCP", sub: "Normalizer", icon: GitCompare, color: "text-violet-400 border-violet-500/30" },
    { key: "trust" as const, label: "Trust MCP", sub: "Integrity", icon: ShieldCheck, color: "text-sky-400 border-sky-500/30" },
  ];

  return (
    <div className="w-full h-full flex items-center justify-center p-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 w-full">
        {nodes.map((n) => {
          const Icon = n.icon;
          const status = nodeStates[n.key];
          return (
            <div
              key={n.key}
              className={`glass rounded-xl p-3 border flex flex-col items-center text-center transition-all ${
                status === "running"
                  ? "border-violet-400/50 bg-violet-500/10 shadow-lg shadow-violet-500/10"
                  : status === "completed"
                  ? `${n.color} bg-slate-900/60`
                  : status === "failed"
                  ? "border-red-500/40 bg-red-500/10"
                  : "border-slate-800 bg-slate-950/50 opacity-70"
              }`}
            >
              <Icon className={`w-6 h-6 mb-2 ${status === "pending" ? "text-slate-500" : n.color.split(" ")[0]}`} />
              <div className="text-xs font-semibold text-slate-200">{n.label}</div>
              <div className="text-[10px] text-slate-500 mb-2">{n.sub}</div>
              <StatusBadge status={status} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function subscribeReducedMotion(callback: () => void) {
  if (typeof window === "undefined") return () => {};
  const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
  mq.addEventListener("change", callback);
  return () => mq.removeEventListener("change", callback);
}

function getReducedMotionSnapshot(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function MCPPipeline3DWrapper({ nodeStates }: { nodeStates: MCPNodeState }) {
  const reducedMotion = useSyncExternalStore(
    subscribeReducedMotion,
    getReducedMotionSnapshot,
    () => false
  );

  const webgl = checkWebGLSupport();

  return (
    <div className="relative w-full h-64 sm:h-72 rounded-2xl glass border border-cyan-500/20 overflow-hidden bg-slate-950/60 mb-6 flex flex-col">
      <div className="absolute top-3 left-4 z-10 flex items-center gap-2 pointer-events-none">
        <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
        <span className="text-[11px] font-mono uppercase tracking-wider text-cyan-400/90">
          3D MCP Execution Mesh
        </span>
      </div>

      <div className="flex-1 min-h-0 w-full">
        {webgl ? (
          <MCPPipeline3DLazy nodeStates={nodeStates} reducedMotion={reducedMotion} />
        ) : (
          <MCPPipelineFallback nodeStates={nodeStates} />
        )}
      </div>

      {/* Stable React DOM status bar synced to 3D MCP nodes (avoids Drei Html portal unmount issues in React 19) */}
      {webgl && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 px-3 pb-3 pt-1 z-10 bg-gradient-to-t from-slate-950/90 via-slate-950/50 to-transparent">
          {[
            { key: "browser" as const, label: "Browser MCP", sub: "Playwright" },
            { key: "evidence" as const, label: "Evidence MCP", sub: "SQLite Vault" },
            { key: "comparison" as const, label: "Comparison MCP", sub: "Normalizer" },
            { key: "trust" as const, label: "Trust MCP", sub: "Integrity" },
          ].map((node) => (
            <div
              key={node.key}
              className="flex items-center justify-between gap-2 px-2.5 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800/80 backdrop-blur-md"
            >
              <div className="min-w-0">
                <div className="text-[11px] font-semibold text-slate-200 truncate">{node.label}</div>
                <div className="text-[9px] font-mono text-slate-500 truncate">{node.sub}</div>
              </div>
              <StatusBadge status={nodeStates[node.key]} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
