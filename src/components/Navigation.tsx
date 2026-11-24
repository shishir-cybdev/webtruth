"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import { Search, Menu, X, Zap } from "lucide-react";

const navItems = [
  { label: "Home", href: "/" },
  { label: "Investigate", href: "/investigate" },
  { label: "Compare", href: "/compare" },
  { label: "Evidence", href: "/evidence" },
  { label: "About", href: "/about" },
];

export function Navigation() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <>
      <motion.nav
        initial={{ y: -80, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled ? "glass border-b border-cyan-500/10 shadow-lg shadow-cyan-500/5" : "bg-transparent"
        }`}
        role="navigation"
        aria-label="Main navigation"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2 group" aria-label="WebTruth home">
              <div className="relative">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-violet-500 flex items-center justify-center">
                  <Zap className="w-4 h-4 text-white" />
                </div>
                <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-cyan-400 to-violet-500 blur-md opacity-0 group-hover:opacity-60 transition-opacity duration-300" />
              </div>
              <span className="text-lg font-bold tracking-tight">
                <span className="gradient-text">Web</span>
                <span className="text-slate-200">Truth</span>
              </span>
            </Link>

            {/* Desktop nav */}
            <div className="hidden md:flex items-center gap-1">
              {navItems.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`relative px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                      isActive
                        ? "text-cyan-400"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {isActive && (
                      <motion.span
                        layoutId="nav-active"
                        className="absolute inset-0 rounded-lg glass border border-cyan-500/20 bg-cyan-500/5"
                        transition={{ type: "spring", bounce: 0.2, duration: 0.4 }}
                      />
                    )}
                    <span className="relative">{item.label}</span>
                  </Link>
                );
              })}
            </div>

            {/* CTA + mobile toggle */}
            <div className="flex items-center gap-3">
              <Link
                href="/investigate"
                className="hidden sm:flex items-center gap-2 px-4 py-2 text-sm font-semibold text-navy-950 bg-gradient-to-r from-cyan-400 to-cyan-500 rounded-lg hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-200 hover:scale-105 active:scale-95"
                style={{ color: "#020817" }}
              >
                <Search className="w-3.5 h-3.5" />
                Investigate
              </Link>
              <button
                className="md:hidden p-2 text-slate-400 hover:text-slate-200 transition-colors"
                onClick={() => setMobileOpen(!mobileOpen)}
                aria-label={mobileOpen ? "Close menu" : "Open menu"}
                aria-expanded={mobileOpen}
              >
                {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>
            </div>
          </div>
        </div>
      </motion.nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.2 }}
            className="fixed top-16 left-0 right-0 z-40 glass border-b border-cyan-500/10 md:hidden"
          >
            <div className="max-w-7xl mx-auto px-4 py-4 flex flex-col gap-1">
              {navItems.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    className={`px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? "text-cyan-400 bg-cyan-500/10"
                        : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
              <Link
                href="/investigate"
                onClick={() => setMobileOpen(false)}
                className="mt-2 flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold rounded-lg bg-gradient-to-r from-cyan-400 to-cyan-500 hover:shadow-lg hover:shadow-cyan-500/25 transition-all"
                style={{ color: "#020817" }}
              >
                <Search className="w-4 h-4" />
                Start Investigating
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
