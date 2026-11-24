"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import {
  ChevronRight, AlertTriangle, CheckCircle, Clock, HelpCircle,
  ExternalLink, Shield, Info, ChevronDown, ChevronUp, Eye
} from "lucide-react";
import { SAMPLE_EVIDENCE } from "@/data";
import type { EvidenceRecord } from "@/types";

function formatINR(amount: number) {
  if (amount === 0) return "N/A";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount);
}

const SOURCE_TYPE_CONFIG = {
  retailer: { label: "Retailer", color: "cyan", icon: Shield },
  review: { label: "Review Site", color: "violet", icon: Eye },
  forum: { label: "Community", color: "amber", icon: HelpCircle },
  official: { label: "Official", color: "green", icon: CheckCircle },
  unknown: { label: "Unknown", color: "slate", icon: HelpCircle },
};

const STATUS_CONFIG = {
  verified: { label: "Verified", color: "text-green-400", bg: "border-green-500/20 bg-green-500/5" },
  unverified: { label: "Unverified", color: "text-slate-500", bg: "border-slate-700/40" },
  contradicted: { label: "Contradicted", color: "text-red-400", bg: "border-red-500/20 bg-red-500/5" },
  pending: { label: "Pending Review", color: "text-amber-400", bg: "border-amber-500/20 bg-amber-500/5" },
};

function StatusBadge({ status }: { status: EvidenceRecord["status"] }) {
  const cfg = STATUS_CONFIG[status];
  return (
    <span className={`text-xs font-medium px-2.5 py-1 rounded-full glass border ${cfg.bg} ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

function EvidenceCard({ record, index }: { record: EvidenceRecord; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const typeCfg = SOURCE_TYPE_CONFIG[record.sourceType];
  const TypeIcon = typeCfg.icon;
  const hasContradiction = !!record.contradiction;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.07, duration: 0.4 }}
      className={`glass rounded-2xl border p-5 ${
        hasContradiction ? "border-amber-500/20" : "border-slate-700/30"
      }`}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
            typeCfg.color === "cyan" ? "bg-cyan-500/10" :
            typeCfg.color === "violet" ? "bg-violet-500/10" :
            typeCfg.color === "green" ? "bg-green-500/10" :
            typeCfg.color === "amber" ? "bg-amber-500/10" : "bg-slate-800"
          }`}>
            <TypeIcon className={`w-4 h-4 ${
              typeCfg.color === "cyan" ? "text-cyan-400" :
              typeCfg.color === "violet" ? "text-violet-400" :
              typeCfg.color === "green" ? "text-green-400" :
              typeCfg.color === "amber" ? "text-amber-400" : "text-slate-500"
            }`} />
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-200">{record.source}</div>
            <div className={`text-xs font-medium ${
              typeCfg.color === "cyan" ? "text-cyan-400/70" :
              typeCfg.color === "violet" ? "text-violet-400/70" :
              typeCfg.color === "green" ? "text-green-400/70" :
              typeCfg.color === "amber" ? "text-amber-400/70" : "text-slate-600"
            }`}>{typeCfg.label}</div>
          </div>
        </div>
        <StatusBadge status={record.status} />
      </div>

      {/* Price */}
      {record.claimedPrice > 0 && (
        <div className="mb-3">
          <div className="text-xs text-slate-500 mb-0.5">Claimed Price</div>
          <div className="text-lg font-bold text-slate-200">{formatINR(record.claimedPrice)}</div>
        </div>
      )}

      {/* Contradiction warning */}
      {hasContradiction && (
        <div className="flex items-start gap-2 glass border border-amber-500/20 bg-amber-500/5 rounded-xl px-3 py-2.5 mb-3">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
          <span className="text-xs text-amber-400">{record.contradiction}</span>
        </div>
      )}

      {/* Excerpt */}
      <p className="text-xs text-slate-500 leading-relaxed mb-3">{record.excerpt}</p>

      {/* Phase 2 note */}
      <div className="flex items-start gap-2 glass border border-violet-500/15 bg-violet-500/5 rounded-xl px-3 py-2.5 mb-3">
        <Info className="w-3.5 h-3.5 text-violet-400 shrink-0 mt-0.5" />
        <div className="text-xs text-violet-400">
          <span className="font-semibold">Phase 2:</span> Real evidence will show verified price snapshots, timestamps, confidence scores, and source screenshots.
        </div>
      </div>

      {/* Expand for details */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
        aria-expanded={expanded}
      >
        {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        {expanded ? "Less detail" : "More detail"}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-3 pt-3 border-t border-slate-800 space-y-2 text-xs text-slate-500">
              <div className="flex justify-between">
                <span>Source ID</span>
                <span className="font-mono text-slate-400">{record.id}</span>
              </div>
              <div className="flex justify-between">
                <span>Confidence</span>
                <span className="text-slate-600 italic">Not computed (Phase 2)</span>
              </div>
              <div className="flex justify-between">
                <span>Last Verified</span>
                <span className="text-slate-600 italic">Not crawled (Phase 2)</span>
              </div>
              <div className="flex items-center gap-1 pt-1">
                <ExternalLink className="w-3 h-3" />
                <span className="font-mono text-slate-700">{record.url}</span>
                <span className="text-slate-700">(Phase 2: live link)</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

type FilterType = "all" | EvidenceRecord["sourceType"] | EvidenceRecord["status"];

export default function EvidencePage() {
  const [activeFilter, setActiveFilter] = useState<FilterType>("all");

  const filters: { label: string; value: FilterType; count: number }[] = [
    { label: "All", value: "all", count: SAMPLE_EVIDENCE.length },
    { label: "Contradicted", value: "contradicted", count: SAMPLE_EVIDENCE.filter((e) => e.contradiction).length },
    { label: "Retailers", value: "retailer", count: SAMPLE_EVIDENCE.filter((e) => e.sourceType === "retailer").length },
    { label: "Reviews", value: "review", count: SAMPLE_EVIDENCE.filter((e) => e.sourceType === "review").length },
    { label: "Community", value: "forum", count: SAMPLE_EVIDENCE.filter((e) => e.sourceType === "forum").length },
    { label: "Official", value: "official", count: SAMPLE_EVIDENCE.filter((e) => e.sourceType === "official").length },
  ];

  const filtered = SAMPLE_EVIDENCE.filter((record) => {
    if (activeFilter === "all") return true;
    if (activeFilter === "contradicted") return !!record.contradiction;
    return record.sourceType === activeFilter || record.status === activeFilter;
  });

  return (
    <div className="min-h-screen pt-24 pb-16 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-3">
            <Link href="/" className="hover:text-slate-300 transition-colors">Home</Link>
            <ChevronRight className="w-3 h-3" />
            <span className="text-cyan-400">Evidence</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-100 mb-2">Evidence Explorer</h1>
          <p className="text-slate-400 text-sm max-w-2xl">
            See how WebTruth will gather, classify, and cross-reference evidence from multiple sources in Phase 2.
            These are sample records illustrating the evidence structure.
          </p>
        </motion.div>

        {/* Demo banner */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="flex items-start gap-3 glass border border-amber-500/30 rounded-xl px-5 py-4 text-sm mb-8"
        >
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <div className="text-amber-400 font-semibold mb-1">DEMO MODE — Sample Evidence Structure</div>
            <div className="text-slate-400 text-xs leading-relaxed">
              These records show what evidence cards will look like in Phase 2 when MCP servers are live.
              No prices, URLs, or claims here are real or verified. Contradictions are simulated for demonstration purposes.
            </div>
          </div>
        </motion.div>

        {/* Summary cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          {[
            { label: "Total Sources", value: SAMPLE_EVIDENCE.length, color: "cyan" },
            { label: "Contradictions", value: SAMPLE_EVIDENCE.filter((e) => e.contradiction).length, color: "amber" },
            { label: "Price Variance", value: "₹14K+", color: "red" },
            { label: "Unknown Fields", value: "12", color: "violet" },
          ].map(({ label, value, color }) => (
            <motion.div
              key={label}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className={`glass rounded-xl border p-4 ${
                color === "cyan" ? "border-cyan-500/15" :
                color === "amber" ? "border-amber-500/15" :
                color === "red" ? "border-red-500/15" : "border-violet-500/15"
              }`}
            >
              <div className={`text-2xl font-bold mb-1 ${
                color === "cyan" ? "text-cyan-400" :
                color === "amber" ? "text-amber-400" :
                color === "red" ? "text-red-400" : "text-violet-400"
              }`}>{value}</div>
              <div className="text-xs text-slate-500">{label}</div>
              <div className="text-xs text-slate-700 mt-0.5">Demo data</div>
            </motion.div>
          ))}
        </div>

        {/* Filter tabs */}
        <div className="flex flex-wrap gap-2 mb-6">
          {filters.map((f) => (
            <button
              key={f.value}
              onClick={() => setActiveFilter(f.value)}
              className={`flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium rounded-full border transition-all ${
                activeFilter === f.value
                  ? "border-cyan-500/40 text-cyan-400 bg-cyan-500/10"
                  : "border-slate-700/40 text-slate-500 hover:border-slate-600 hover:text-slate-400"
              }`}
            >
              {f.label}
              <span className={`w-4 h-4 rounded-full text-center leading-4 text-xs ${
                activeFilter === f.value ? "bg-cyan-400 text-navy-950" : "bg-slate-800 text-slate-500"
              }`}
              style={activeFilter === f.value ? { color: "#020817" } : {}}>
                {f.count}
              </span>
            </button>
          ))}
        </div>

        {/* Evidence cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <AnimatePresence>
            {filtered.map((record, i) => (
              <EvidenceCard key={record.id} record={record} index={i} />
            ))}
          </AnimatePresence>
        </div>

        {filtered.length === 0 && (
          <div className="text-center py-16 text-slate-500 text-sm">
            No evidence records match this filter.
          </div>
        )}

        {/* Phase 2 roadmap */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mt-12 glass-violet rounded-2xl border border-violet-500/15 p-8"
        >
          <div className="flex items-center gap-3 mb-4">
            <Clock className="w-5 h-5 text-violet-400" />
            <h2 className="text-lg font-semibold text-slate-100">What Phase 2 Evidence Will Include</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              "Live price snapshots with timestamps",
              "Automated contradiction flagging",
              "Confidence scores per source",
              "Screenshot archives of claimed prices",
              "Spec mismatch detection vs. manufacturer data",
              "Fake review pattern signals",
              "Price history charts",
              "Source credibility ratings",
            ].map((item) => (
              <div key={item} className="flex items-center gap-2 text-sm text-slate-400">
                <div className="w-1.5 h-1.5 rounded-full bg-violet-400 shrink-0" />
                {item}
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
