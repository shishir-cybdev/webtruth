import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Navigation } from "@/components/Navigation";
import { PageTransition } from "@/components/PageTransition";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "WebTruth — Investigate Every Deal",
  description: "Don't just compare prices. Investigate the truth behind every deal. AI-powered product investigation platform.",
  keywords: ["product investigation", "price comparison", "AI research", "consumer intelligence"],
  openGraph: {
    title: "WebTruth — Don't just compare prices. Investigate the truth.",
    description: "AI-powered product investigation platform",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="antialiased min-h-screen" style={{ background: "#020817" }}>
        <div className="scanline" aria-hidden="true" />
        <Navigation />
        <PageTransition>
          {children}
        </PageTransition>
      </body>
    </html>
  );
}
