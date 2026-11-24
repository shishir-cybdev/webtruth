"use client";

import { useRef, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, useScroll, useTransform, useMotionValue, useSpring } from "motion/react";
import { Search, Shield, Zap, Eye, ChevronRight, TrendingDown, BarChart3, FileSearch, ArrowRight } from "lucide-react";
import { HeroSceneWrapper } from "@/components/HeroSceneWrapper";

const CATEGORIES = ["Laptops", "Smartphones", "Headphones", "Monitors", "Tablets", "Cameras"];

const FEATURES = [
  {
    icon: Search,
    title: "Deep Price Intelligence",
    description: "Cross-reference prices from 50+ Indian retailers in real-time. Spot hidden fees and misleading discounts.",
    color: "cyan",
    gradient: "from-cyan-500/20 to-cyan-500/5",
    border: "border-cyan-500/20",
  },
  {
    icon: Shield,
    title: "Contradiction Detection",
    description: "Automatically flag when specs or prices claimed by sellers don't match official data sources.",
    color: "violet",
    gradient: "from-violet-500/20 to-violet-500/5",
    border: "border-violet-500/20",
  },
  {
    icon: Eye,
    title: "Review Authenticity",
    description: "Semantic analysis to surface genuine user experiences and detect coordinated fake review patterns.",
    color: "green",
    gradient: "from-green-500/20 to-green-500/5",
    border: "border-green-500/20",
  },
  {
    icon: BarChart3,
    title: "Evidence Timeline",
    description: "Track how prices and product information change over time. Know when to buy, not just what to buy.",
    color: "cyan",
    gradient: "from-cyan-500/20 to-cyan-500/5",
    border: "border-cyan-500/20",
  },
  {
    icon: FileSearch,
    title: "Specification Verification",
    description: "Every claimed spec is cross-checked against manufacturer datasheets and independent lab results.",
    color: "violet",
    gradient: "from-violet-500/20 to-violet-500/5",
    border: "border-violet-500/20",
  },
  {
    icon: TrendingDown,
    title: "Price Drop Alerts",
    description: "Set intelligent alerts based on historical price patterns. Never overpay again.",
    color: "green",
    gradient: "from-green-500/20 to-green-500/5",
    border: "border-green-500/20",
  },
];

function HeroSearchBar() {
  const [query, setQuery] = useState("");
  const router = useRouter();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/investigate?q=${encodeURIComponent(query.trim())}`);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative max-w-2xl mx-auto">
      <div className="relative group">
        <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-500 to-violet-500 rounded-2xl opacity-30 group-hover:opacity-50 transition-opacity duration-300 blur-sm" />
        <div className="relative flex items-center glass rounded-2xl border border-cyan-500/20">
          <Search className="absolute left-5 w-5 h-5 text-cyan-400 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='Try "Dell XPS 15 laptop" or "Sony WH-1000XM5"…'
            className="w-full bg-transparent pl-13 pr-36 py-5 text-slate-200 placeholder-slate-500 focus:outline-none text-base"
            aria-label="Search for a product to investigate"
            style={{ paddingLeft: "3.25rem" }}
          />
          <button
            type="submit"
            className="absolute right-2 flex items-center gap-2 px-5 py-3 text-sm font-semibold rounded-xl bg-gradient-to-r from-cyan-400 to-cyan-500 hover:shadow-lg hover:shadow-cyan-500/30 transition-all duration-200 hover:scale-105 active:scale-95 focus:outline-none focus:ring-2 focus:ring-cyan-400"
            style={{ color: "#020817" }}
          >
            <Zap className="w-4 h-4" />
            Investigate
          </button>
        </div>
      </div>
    </form>
  );
}

function FeatureCard({ feature, index }: { feature: typeof FEATURES[0]; index: number }) {
  const Icon = feature.icon;
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.5, delay: index * 0.08, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className={`glass rounded-2xl p-6 border ${feature.border} bg-gradient-to-br ${feature.gradient} cursor-default`}
    >
      <div className={`w-10 h-10 rounded-xl mb-4 flex items-center justify-center ${
        feature.color === "cyan" ? "bg-cyan-500/15" :
        feature.color === "violet" ? "bg-violet-500/15" : "bg-green-500/15"
      }`}>
        <Icon className={`w-5 h-5 ${
          feature.color === "cyan" ? "text-cyan-400" :
          feature.color === "violet" ? "text-violet-400" : "text-green-400"
        }`} />
      </div>
      <h3 className="text-base font-semibold text-slate-100 mb-2">{feature.title}</h3>
      <p className="text-sm text-slate-400 leading-relaxed">{feature.description}</p>
    </motion.div>
  );
}

export default function HomePage() {
  const heroRef = useRef<HTMLDivElement>(null);
  const { scrollY } = useScroll();
  const heroOpacity = useTransform(scrollY, [0, 400], [1, 0]);
  const heroY = useTransform(scrollY, [0, 400], [0, -60]);
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 50, damping: 20 });
  const springY = useSpring(mouseY, { stiffness: 50, damping: 20 });

  useEffect(() => {
    const handle = (e: MouseEvent) => {
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      mouseX.set((e.clientX - cx) / cx * 15);
      mouseY.set((e.clientY - cy) / cy * 10);
    };
    window.addEventListener("mousemove", handle, { passive: true });
    return () => window.removeEventListener("mousemove", handle);
  }, [mouseX, mouseY]);

  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section ref={heroRef} className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden pt-16">
        {/* 3D Background */}
        <div className="absolute inset-0 grid-pattern opacity-50" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[#020817]" />

        {/* 3D Scene */}
        <motion.div className="absolute inset-0" style={{ x: springX, y: springY }}>
          <HeroSceneWrapper />
        </motion.div>

        {/* Gradient radial glow */}
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute top-1/3 left-1/3 w-[400px] h-[400px] bg-violet-500/5 rounded-full blur-3xl pointer-events-none" />

        {/* Hero content */}
        <motion.div
          style={{ opacity: heroOpacity, y: heroY }}
          className="relative z-10 max-w-5xl mx-auto px-4 text-center"
        >
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="inline-flex items-center gap-2 glass border border-cyan-500/20 rounded-full px-4 py-2 text-xs font-medium text-cyan-400 mb-8"
          >
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            Phase 1 · Frontend Preview · DEMO MODE
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
            className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight leading-none mb-6"
          >
            <span className="text-slate-100">Don&apos;t just </span>
            <span className="gradient-text">compare</span>
            <span className="text-slate-100"> prices.</span>
            <br />
            <span className="gradient-text">Investigate</span>
            <span className="text-slate-100"> the truth.</span>
          </motion.h1>

          {/* Subheadline */}
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.35 }}
            className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed"
          >
            WebTruth uses AI and MCP intelligence agents to investigate every deal — surfacing hidden fees, fake reviews, spec mismatches, and pricing contradictions before you buy.
          </motion.p>

          {/* Search */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="mb-8"
          >
            <HeroSearchBar />
          </motion.div>

          {/* Category chips */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.65 }}
            className="flex flex-wrap justify-center gap-2"
          >
            <span className="text-xs text-slate-500 self-center mr-1">Trending:</span>
            {CATEGORIES.map((cat) => (
              <Link
                key={cat}
                href={`/investigate?q=${encodeURIComponent(cat)}`}
                className="px-3 py-1.5 text-xs font-medium glass border border-slate-700/50 rounded-full text-slate-400 hover:text-cyan-400 hover:border-cyan-500/30 transition-all duration-200 hover:scale-105"
              >
                {cat}
              </Link>
            ))}
          </motion.div>
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-slate-500"
        >
          <span className="text-xs">Scroll to explore</span>
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
            className="w-5 h-8 rounded-full border border-slate-600 flex items-start justify-center pt-1.5"
          >
            <div className="w-1 h-2 rounded-full bg-cyan-400" />
          </motion.div>
        </motion.div>
      </section>

      {/* Stats bar */}
      <section className="relative py-12 border-y border-cyan-500/10 bg-gradient-to-r from-transparent via-cyan-500/5 to-transparent">
        <div className="max-w-6xl mx-auto px-4 grid grid-cols-2 sm:grid-cols-4 gap-8">
          {[
            { label: "MCP Intelligence Servers", value: "5+", note: "Planned for Phase 2" },
            { label: "Data Sources Crawled", value: "50+", note: "In development" },
            { label: "Products Indexed", value: "10K+", note: "Target at launch" },
            { label: "Contradictions Caught", value: "∞", note: "Every deal scrutinised" },
          ].map((stat) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="text-center"
            >
              <div className="text-3xl font-bold gradient-text mb-1">{stat.value}</div>
              <div className="text-sm text-slate-400 font-medium">{stat.label}</div>
              <div className="text-xs text-slate-600 mt-0.5">{stat.note}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Features grid */}
      <section className="py-24 px-4">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <div className="inline-flex items-center gap-2 glass border border-violet-500/20 rounded-full px-4 py-1.5 text-xs font-medium text-violet-400 mb-4">
              <Zap className="w-3 h-3" />
              Intelligence Platform
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-100 mb-4">
              Every deal deserves an investigation
            </h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              Six specialised intelligence modules work together to give you a complete picture before you spend.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map((feature, i) => (
              <FeatureCard key={feature.title} feature={feature} index={i} />
            ))}
          </div>
        </div>
      </section>

      {/* CTA section */}
      <section className="py-24 px-4 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-violet-500/5" />
        <div className="max-w-3xl mx-auto text-center relative z-10">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="glass-violet rounded-3xl p-12 border border-violet-500/15 shadow-2xl shadow-violet-500/5"
          >
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-100 mb-4">
              Ready to investigate?
            </h2>
            <p className="text-slate-400 mb-8 leading-relaxed">
              Search any product and watch WebTruth&apos;s AI agents cross-reference prices, verify specs, and surface the truth.{" "}
              <span className="text-amber-400 font-medium">Currently showing demo data — Phase 2 brings live intelligence.</span>
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/investigate"
                className="flex items-center justify-center gap-2 px-8 py-4 font-semibold rounded-xl bg-gradient-to-r from-cyan-400 to-cyan-500 hover:shadow-xl hover:shadow-cyan-500/30 transition-all duration-200 hover:scale-105 active:scale-95 text-sm"
                style={{ color: "#020817" }}
              >
                Start Investigation
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/compare"
                className="flex items-center justify-center gap-2 px-8 py-4 font-semibold rounded-xl glass border border-cyan-500/20 text-cyan-400 hover:border-cyan-400/40 transition-all duration-200 hover:scale-105 text-sm"
              >
                Compare Products
                <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800/50 py-10 px-4">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-500">
          <div className="flex items-center gap-2">
            <span className="gradient-text font-bold">WebTruth</span>
            <span>· Phase 1 Frontend Preview</span>
          </div>
          <div className="flex gap-6">
            <Link href="/about" className="hover:text-slate-300 transition-colors">About</Link>
            <Link href="/evidence" className="hover:text-slate-300 transition-colors">Evidence</Link>
            <span className="text-slate-700">© 2024</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
