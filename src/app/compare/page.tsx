"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import { Check, ChevronRight, ArrowUpDown, Filter, Info, Star, Zap, X, ChevronDown, ChevronUp } from "lucide-react";
import { SAMPLE_PRODUCTS } from "@/data";
import type { Product } from "@/types";

function formatINR(amount: number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount);
}

const SORT_OPTIONS = [
  { label: "Price: Low to High", value: "price-asc" },
  { label: "Price: High to Low", value: "price-desc" },
  { label: "Trust Score", value: "score-desc" },
  { label: "Name A–Z", value: "name-asc" },
];

const ALL_TAGS = Array.from(new Set(SAMPLE_PRODUCTS.flatMap((p) => p.tags)));

function ProductCard({
  product,
  selected,
  onToggle,
  isDisabled,
}: {
  product: Product;
  selected: boolean;
  onToggle: () => void;
  isDisabled: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      whileHover={{ y: -4 }}
      transition={{ duration: 0.3 }}
      className={`relative glass rounded-2xl border p-5 cursor-pointer transition-all duration-200 ${
        selected
          ? "border-cyan-500/40 shadow-lg shadow-cyan-500/10 bg-cyan-500/5"
          : isDisabled
          ? "border-slate-800/50 opacity-50 cursor-not-allowed"
          : "border-slate-700/30 hover:border-cyan-500/20"
      }`}
      onClick={() => !isDisabled || selected ? onToggle() : null}
    >
      {/* Selection badge */}
      <div className={`absolute top-4 right-4 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all duration-200 ${
        selected ? "bg-cyan-400 border-cyan-400" : "border-slate-600"
      }`}>
        {selected && <Check className="w-3.5 h-3.5" style={{ color: "#020817" }} />}
      </div>

      {/* Badge */}
      {product.badge && (
        <div className="inline-flex items-center gap-1.5 glass border border-violet-500/20 rounded-full px-2.5 py-1 text-xs font-medium text-violet-400 mb-3">
          <Star className="w-3 h-3" />
          {product.badge}
        </div>
      )}

      {/* Product info */}
      <div className="mb-3">
        <div className="text-xs text-slate-500 font-medium mb-0.5">{product.brand}</div>
        <h3 className="text-base font-semibold text-slate-100 leading-tight pr-8">{product.name}</h3>
      </div>

      {/* Price */}
      <div className="mb-4">
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-cyan-400">{formatINR(product.price)}</span>
        </div>
        <div className="flex items-center gap-1.5 mt-1">
          <Info className="w-3 h-3 text-amber-400 shrink-0" />
          <span className="text-xs text-amber-400">Illustrative sample price — not live data</span>
        </div>
      </div>

      {/* Score */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
          <motion.div
            className={`h-full rounded-full ${
              product.score >= 90 ? "bg-gradient-to-r from-green-400 to-cyan-400" :
              product.score >= 80 ? "bg-gradient-to-r from-cyan-400 to-cyan-500" :
              "bg-gradient-to-r from-amber-400 to-cyan-400"
            }`}
            initial={{ width: 0 }}
            animate={{ width: `${product.score}%` }}
            transition={{ delay: 0.3, duration: 0.8, ease: "easeOut" }}
          />
        </div>
        <span className="text-xs font-semibold text-slate-400">{product.score}/100</span>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {product.tags.map((tag) => (
          <span key={tag} className="text-xs glass border border-slate-700/40 text-slate-500 px-2 py-0.5 rounded-full">
            {tag}
          </span>
        ))}
      </div>

      {/* Expandable specs */}
      <button
        onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
        className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
        aria-expanded={expanded}
      >
        {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        {expanded ? "Hide specs" : "Show key specs"}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-3 pt-3 border-t border-slate-800 space-y-1.5">
              {Object.entries(product.specs).slice(0, 5).map(([key, val]) => (
                <div key={key} className="flex justify-between text-xs">
                  <span className="text-slate-500">{key}</span>
                  <span className="text-slate-300 font-medium text-right ml-4">{val}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function ComparisonTable({ products }: { products: Product[] }) {
  if (products.length === 0) return null;

  const allSpecKeys = Array.from(new Set(products.flatMap((p) => Object.keys(p.specs))));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="glass rounded-2xl border border-cyan-500/15 overflow-hidden"
    >
      <div className="p-5 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-100">Side-by-Side Comparison</h2>
          <p className="text-xs text-amber-400 mt-0.5">
            <Info className="w-3 h-3 inline mr-1" />
            All prices are illustrative sample data — not live
          </p>
        </div>
        <span className="text-xs text-slate-500">{products.length} products</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm" role="table" aria-label="Product comparison table">
          <thead>
            <tr className="border-b border-slate-800">
              <th className="text-left p-4 text-slate-500 font-medium w-32 shrink-0">Specification</th>
              {products.map((p) => (
                <th key={p.id} className="text-left p-4 min-w-48">
                  <div className="text-xs text-slate-500">{p.brand}</div>
                  <div className="text-slate-100 font-semibold leading-tight">{p.name}</div>
                  <div className="text-cyan-400 font-bold mt-1">{formatINR(p.price)}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-slate-800/50 bg-cyan-500/5">
              <td className="p-4 text-slate-500 font-medium text-xs">Trust Score</td>
              {products.map((p) => (
                <td key={p.id} className="p-4">
                  <span className={`text-sm font-bold ${p.score >= 90 ? "text-green-400" : p.score >= 80 ? "text-cyan-400" : "text-amber-400"}`}>
                    {p.score} / 100
                  </span>
                </td>
              ))}
            </tr>
            {allSpecKeys.map((key, i) => (
              <tr key={key} className={`border-b border-slate-800/30 ${i % 2 === 0 ? "" : "bg-slate-900/20"}`}>
                <td className="p-4 text-slate-500 text-xs font-medium">{key}</td>
                {products.map((p) => (
                  <td key={p.id} className="p-4 text-slate-300 text-xs">
                    {p.specs[key] || <span className="text-slate-700">—</span>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}

export default function ComparePage() {
  const [selected, setSelected] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState("score-desc");
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [showComparison, setShowComparison] = useState(false);

  const toggleProduct = (id: string) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 3) return prev;
      return [...prev, id];
    });
  };

  const sorted = useMemo(() => {
    let list = [...SAMPLE_PRODUCTS];
    if (activeTag) list = list.filter((p) => p.tags.includes(activeTag));
    switch (sortBy) {
      case "price-asc": return list.sort((a, b) => a.price - b.price);
      case "price-desc": return list.sort((a, b) => b.price - a.price);
      case "score-desc": return list.sort((a, b) => b.score - a.score);
      case "name-asc": return list.sort((a, b) => a.name.localeCompare(b.name));
      default: return list;
    }
  }, [sortBy, activeTag]);

  const selectedProducts = SAMPLE_PRODUCTS.filter((p) => selected.includes(p.id));

  return (
    <div className="min-h-screen pt-24 pb-16 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-3">
            <Link href="/" className="hover:text-slate-300 transition-colors">Home</Link>
            <ChevronRight className="w-3 h-3" />
            <span className="text-cyan-400">Compare</span>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-end gap-4 justify-between">
            <div>
              <h1 className="text-3xl sm:text-4xl font-bold text-slate-100 mb-2">Compare Products</h1>
              <p className="text-slate-400 text-sm">
                Select up to 3 products to compare side by side ·{" "}
                <span className="text-amber-400">Sample laptop data — illustrative only</span>
              </p>
            </div>
            <div className="shrink-0">
              {selected.length > 0 && (
                <motion.button
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  onClick={() => setShowComparison(!showComparison)}
                  className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold rounded-xl bg-gradient-to-r from-cyan-400 to-cyan-500 hover:shadow-lg hover:shadow-cyan-500/25 transition-all"
                  style={{ color: "#020817" }}
                >
                  <Zap className="w-4 h-4" />
                  {showComparison ? "Hide" : "Compare"} ({selected.length})
                </motion.button>
              )}
            </div>
          </div>
        </motion.div>

        {/* Selection counter */}
        <AnimatePresence>
          {selected.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="flex items-center gap-3 glass border border-cyan-500/20 rounded-xl px-5 py-3 mb-6 text-sm"
            >
              <Check className="w-4 h-4 text-cyan-400" />
              <span className="text-slate-300">
                {selected.length} of 3 products selected
              </span>
              <button
                onClick={() => setSelected([])}
                className="ml-auto flex items-center gap-1 text-slate-500 hover:text-slate-300 transition-colors text-xs"
              >
                <X className="w-3.5 h-3.5" /> Clear
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Comparison table */}
        <AnimatePresence>
          {showComparison && selectedProducts.length > 0 && (
            <motion.div className="mb-8">
              <ComparisonTable products={selectedProducts} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-6">
          {/* Sort */}
          <div className="flex items-center gap-2 glass border border-slate-700/40 rounded-xl px-4 py-2.5">
            <ArrowUpDown className="w-3.5 h-3.5 text-slate-500" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-transparent text-sm text-slate-300 focus:outline-none cursor-pointer"
              aria-label="Sort products"
            >
              {SORT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value} className="bg-slate-900">{o.label}</option>
              ))}
            </select>
          </div>

          {/* Tag filter */}
          <div className="flex items-center gap-2 flex-wrap">
            <Filter className="w-3.5 h-3.5 text-slate-500 ml-1" />
            <button
              onClick={() => setActiveTag(null)}
              className={`px-3 py-1.5 text-xs rounded-full border transition-all ${
                !activeTag ? "border-cyan-500/40 text-cyan-400 bg-cyan-500/10" : "border-slate-700/40 text-slate-500 hover:border-slate-600"
              }`}
            >
              All
            </button>
            {ALL_TAGS.map((tag) => (
              <button
                key={tag}
                onClick={() => setActiveTag(activeTag === tag ? null : tag)}
                className={`px-3 py-1.5 text-xs rounded-full border transition-all ${
                  activeTag === tag ? "border-cyan-500/40 text-cyan-400 bg-cyan-500/10" : "border-slate-700/40 text-slate-500 hover:border-slate-600"
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>

        {/* Product grid */}
        <motion.div layout className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          <AnimatePresence>
            {sorted.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                selected={selected.includes(product.id)}
                onToggle={() => toggleProduct(product.id)}
                isDisabled={!selected.includes(product.id) && selected.length >= 3}
              />
            ))}
          </AnimatePresence>
        </motion.div>

        {sorted.length === 0 && (
          <div className="text-center py-16 text-slate-500">
            No products match the selected filter.
          </div>
        )}
      </div>
    </div>
  );
}
