"use client";

import { motion } from "motion/react";
import Link from "next/link";
import { ChevronRight, Shield, Zap, Eye, Lock, Server, Globe, ArrowRight, CheckCircle } from "lucide-react";
import { MCP_SERVERS } from "@/data";

function MCPServerCard({ server, index }: { server: typeof MCP_SERVERS[0]; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      whileHover={{ y: -4 }}
      className="glass rounded-2xl border border-slate-700/30 hover:border-cyan-500/20 p-5 transition-all duration-200"
    >
      <div className="flex items-start gap-4">
        <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-cyan-500/20 to-violet-500/20 border border-cyan-500/15 flex items-center justify-center text-xl shrink-0">
          {server.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold text-slate-100">{server.name}</h3>
            <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${
              server.status === "active"
                ? "border-green-500/30 text-green-400 bg-green-500/10"
                : server.status === "prototype"
                ? "border-cyan-500/30 text-cyan-400 bg-cyan-500/10"
                : "border-slate-700 text-slate-600"
            }`}>
              {server.status === "planned" ? "Phase 2" : server.status}
            </span>
          </div>
          <p className="text-xs text-slate-500 mb-3 leading-relaxed">{server.description}</p>
          <div className="flex flex-wrap gap-1.5">
            {server.tools.map((tool) => (
              <code key={tool} className="text-xs font-mono bg-slate-900/60 border border-slate-800 text-cyan-400/80 px-2 py-0.5 rounded">
                {tool}
              </code>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function ArchitectureDiagram() {
  return (
    <div className="relative">
      <div className="glass rounded-2xl border border-cyan-500/15 p-8 overflow-hidden">
        {/* Grid bg */}
        <div className="absolute inset-0 grid-pattern opacity-30 rounded-2xl" />
        <div className="relative z-10">
          {/* User layer */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-3 glass border border-violet-500/20 rounded-full px-5 py-3">
              <Globe className="w-4 h-4 text-violet-400" />
              <span className="text-sm font-medium text-violet-400">User Query</span>
            </div>
          </div>

          {/* Arrow */}
          <div className="flex justify-center mb-6">
            <div className="flex flex-col items-center">
              <div className="w-0.5 h-6 bg-gradient-to-b from-violet-400 to-cyan-400" />
              <ArrowRight className="w-3 h-3 text-cyan-400 rotate-90 -mt-1" />
            </div>
          </div>

          {/* Orchestrator */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-3 bg-gradient-to-r from-cyan-500/20 to-violet-500/20 border border-cyan-500/30 rounded-xl px-6 py-3.5">
              <Zap className="w-5 h-5 text-cyan-400" />
              <span className="text-sm font-semibold text-slate-100">WebTruth Orchestrator</span>
              <span className="text-xs text-slate-500">· Gemini 2.0 Flash</span>
            </div>
          </div>

          {/* Arrow */}
          <div className="flex justify-center mb-6">
            <div className="flex flex-col items-center">
              <div className="w-0.5 h-6 bg-gradient-to-b from-cyan-400 to-cyan-400/30" />
              <ArrowRight className="w-3 h-3 text-cyan-400 rotate-90 -mt-1" />
            </div>
          </div>

          {/* MCP layer */}
          <div className="mb-6">
            <div className="text-center text-xs text-slate-500 mb-4 font-medium tracking-wider uppercase">MCP Intelligence Servers</div>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {["PriceSpider", "ReviewSense", "SpecVerify", "TrustScore", "PriceAlert"].map((name) => (
                <div key={name} className="glass border border-slate-700/40 rounded-xl p-3 text-center">
                  <Server className="w-4 h-4 text-cyan-400 mx-auto mb-1.5" />
                  <span className="text-xs text-slate-400 font-medium">{name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Arrow */}
          <div className="flex justify-center mb-6">
            <div className="flex flex-col items-center">
              <div className="w-0.5 h-6 bg-gradient-to-b from-cyan-400/30 to-green-400" />
              <ArrowRight className="w-3 h-3 text-green-400 rotate-90 -mt-1" />
            </div>
          </div>

          {/* Data sources */}
          <div>
            <div className="text-center text-xs text-slate-500 mb-4 font-medium tracking-wider uppercase">Live Data Sources</div>
            <div className="flex flex-wrap justify-center gap-2">
              {["Amazon.in", "Flipkart", "Croma", "Official Sites", "Review Forums", "Manufacturer DBs"].map((src) => (
                <span key={src} className="text-xs text-slate-500 glass border border-slate-800 px-3 py-1.5 rounded-full">
                  {src}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
      <div className="absolute inset-0 rounded-2xl pointer-events-none" style={{
        background: "radial-gradient(ellipse at top, rgba(34,211,238,0.03) 0%, transparent 70%)"
      }} />
    </div>
  );
}

const PRIVACY_PRINCIPLES = [
  {
    icon: Lock,
    title: "No Personal Data Stored",
    description: "WebTruth investigates products, not people. No search history, no user profiling, no tracking cookies.",
  },
  {
    icon: Eye,
    title: "Transparent Sources",
    description: "Every claim is linked to its source. We show you the evidence, not just a conclusion.",
  },
  {
    icon: Shield,
    title: "Honest About Uncertainty",
    description: "Unknown values are labelled unknown. We flag contradictions rather than pick a winner arbitrarily.",
  },
  {
    icon: CheckCircle,
    title: "No Affiliate Incentives",
    description: "WebTruth has no affiliate links. Our scores cannot be purchased or influenced by retailers.",
  },
];

export default function AboutPage() {
  return (
    <div className="min-h-screen pt-24 pb-16 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-4">
            <Link href="/" className="hover:text-slate-300 transition-colors">Home</Link>
            <ChevronRight className="w-3 h-3" />
            <span className="text-cyan-400">About</span>
          </div>
          <div className="inline-flex items-center gap-2 glass border border-cyan-500/20 rounded-full px-4 py-1.5 text-xs font-medium text-cyan-400 mb-5">
            <Zap className="w-3 h-3" />
            Phase 1 · Hackathon Build · Frontend Preview
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold text-slate-100 mb-4 leading-tight">
            Built for consumers who deserve the truth.
          </h1>
          <p className="text-lg text-slate-400 max-w-2xl leading-relaxed">
            WebTruth is an MCP-powered product investigation platform that goes beyond price comparison — it investigates the entire picture: pricing consistency, review authenticity, specification accuracy, and hidden contradictions.
          </p>
        </motion.div>

        {/* Mission */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="glass-violet rounded-2xl border border-violet-500/15 p-8 mb-12"
        >
          <h2 className="text-xl font-bold text-slate-100 mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-violet-400" />
            Our Mission
          </h2>
          <p className="text-slate-400 leading-relaxed mb-4">
            The Indian e-commerce ecosystem is vast and fragmented. The same product can be listed at wildly different prices across platforms, with conflicting specifications, manipulated reviews, and misleading &quot;deals&quot; that aren&apos;t really deals at all.
          </p>
          <p className="text-slate-400 leading-relaxed">
            WebTruth applies AI reasoning and multiple intelligence agents (MCP servers) to give every consumer an independent, evidence-backed investigation — the same rigour a journalist or analyst would apply, done in seconds.
          </p>
        </motion.div>

        {/* Architecture */}
        <div className="mb-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mb-6"
          >
            <h2 className="text-2xl font-bold text-slate-100 mb-2 flex items-center gap-2">
              <Server className="w-5 h-5 text-cyan-400" />
              System Architecture
            </h2>
            <p className="text-slate-400 text-sm">
              Planned Phase 2 architecture — not yet live. All components below are in design/development.
            </p>
          </motion.div>
          <ArchitectureDiagram />
        </div>

        {/* MCP Servers */}
        <div className="mb-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mb-6"
          >
            <h2 className="text-2xl font-bold text-slate-100 mb-2">Intelligence Servers</h2>
            <p className="text-slate-400 text-sm">
              Five specialised MCP servers planned for Phase 2, each owning a distinct domain of investigation.
            </p>
          </motion.div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {MCP_SERVERS.map((server, i) => (
              <MCPServerCard key={server.id} server={server} index={i} />
            ))}
          </div>
        </div>

        {/* Privacy */}
        <div className="mb-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mb-6"
          >
            <h2 className="text-2xl font-bold text-slate-100 mb-2 flex items-center gap-2">
              <Lock className="w-5 h-5 text-cyan-400" />
              Privacy Principles
            </h2>
            <p className="text-slate-400 text-sm">Our commitments to users, by design.</p>
          </motion.div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {PRIVACY_PRINCIPLES.map((principle, i) => {
              const Icon = principle.icon;
              return (
                <motion.div
                  key={principle.title}
                  initial={{ opacity: 0, y: 16 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.08 }}
                  className="glass rounded-2xl border border-cyan-500/10 p-5"
                >
                  <div className="w-9 h-9 rounded-xl bg-cyan-500/10 flex items-center justify-center mb-3">
                    <Icon className="w-4 h-4 text-cyan-400" />
                  </div>
                  <h3 className="text-sm font-semibold text-slate-100 mb-1.5">{principle.title}</h3>
                  <p className="text-xs text-slate-500 leading-relaxed">{principle.description}</p>
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Phase roadmap */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="glass rounded-2xl border border-cyan-500/15 p-8"
        >
          <h2 className="text-xl font-bold text-slate-100 mb-6">Build Roadmap</h2>
          <div className="space-y-6">
            {[
              {
                phase: "Phase 1",
                label: "Current · Hackathon Frontend",
                status: "current",
                items: ["Next.js 15 App Router + TypeScript", "Three.js / R3F 3D hero scene", "All 5 pages with demo data", "Animated UI system (Motion for React)", "Reusable typed component architecture"],
              },
              {
                phase: "Phase 2",
                label: "Upcoming · MCP Backend + Live Data",
                status: "planned",
                items: ["5 MCP intelligence servers", "Live price crawling (50+ sources)", "LLM-powered review analysis", "Specification verification engine", "Real-time trust score computation"],
              },
              {
                phase: "Phase 3",
                label: "Future · Product & Scale",
                status: "future",
                items: ["Price drop alert system", "Mobile app (React Native)", "API access for developers", "Browser extension", "Personalised watchlists"],
              },
            ].map((phase) => (
              <div key={phase.phase} className="flex gap-5">
                <div className="flex flex-col items-center">
                  <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center shrink-0 ${
                    phase.status === "current" ? "border-cyan-400 bg-cyan-400/10" :
                    phase.status === "planned" ? "border-violet-400 bg-violet-400/10" : "border-slate-700 bg-slate-800"
                  }`}>
                    {phase.status === "current" && <div className="w-2.5 h-2.5 rounded-full bg-cyan-400" />}
                    {phase.status === "planned" && <div className="w-2.5 h-2.5 rounded-full bg-violet-400 opacity-60" />}
                    {phase.status === "future" && <div className="w-2.5 h-2.5 rounded-full bg-slate-600" />}
                  </div>
                  <div className="w-0.5 flex-1 bg-slate-800 mt-2" />
                </div>
                <div className="pb-6 flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-sm font-bold ${
                      phase.status === "current" ? "text-cyan-400" :
                      phase.status === "planned" ? "text-violet-400" : "text-slate-600"
                    }`}>{phase.phase}</span>
                    <span className="text-xs text-slate-600">{phase.label}</span>
                  </div>
                  <ul className="space-y-1">
                    {phase.items.map((item) => (
                      <li key={item} className="flex items-center gap-2 text-xs text-slate-500">
                        <div className={`w-1 h-1 rounded-full ${
                          phase.status === "current" ? "bg-cyan-400" :
                          phase.status === "planned" ? "bg-violet-400/60" : "bg-slate-700"
                        }`} />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
