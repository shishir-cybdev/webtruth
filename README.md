# WebTruth — Phase 1 Frontend Preview

> **"Don't just compare prices. Investigate the truth behind every deal."**

WebTruth is an AI and MCP-powered product investigation platform designed to scrutinize consumer purchases across e-commerce ecosystems. While traditional comparison sites stop at listing prices, WebTruth cross-references live pricing, verifies technical specifications against manufacturer datasheets, flags review manipulation, and surfaces inconsistencies before you spend.

---

> [!IMPORTANT]
> **Phase 1 Status: Frontend Only (Demo Mode)**
> This is an interactive frontend prototype built for evaluation and hackathon presentation. All product prices, review scores, contradictions, and MCP pipeline steps are **illustrative sample data**. No real MCP servers, live crawlers, or LLM investigations are connected in Phase 1.

---

## Tech Stack

- **Framework:** Next.js 16 (App Router) with TypeScript
- **Styling:** Tailwind CSS with custom glassmorphism and cybersecurity design tokens
- **3D Graphics:** Three.js, `@react-three/fiber`, `@react-three/drei`
- **Animations:** Motion for React (`motion/react`)
- **Icons:** Lucide React (`lucide-react`)
- **Zero Paid Dependencies:** No proprietary libraries or API keys required

---

## Pages & Features

### 1. Home (`/`)
- **3D Interactive Hero:** Dynamic wireframe globe, orbiting glowing nodes, coordinate rings, and starfield rendered with Three.js.
- **WebGL Fallback:** Gracefully degrades to CSS rings if WebGL is unsupported or disabled.
- **Product Investigation Bar:** Functional search bar that routes queries directly into the investigation pipeline.
- **Trending Category Chips:** Quick-access chips ("Laptops", "Smartphones", etc.) with deep-linking.
- **Feature Cards:** 6 interactive cards detailing planned intelligence modules.

### 2. Investigate (`/investigate`)
- **Simulated Pipeline Execution:** Step-by-step visual animation demonstrating how MCP intelligence servers will orchestrate:
  1. *Query Understanding* (`PriceSpider MCP`)
  2. *Live Price Crawl* (`PriceSpider MCP`)
  3. *Review Intelligence* (`ReviewSense MCP`)
  4. *Specification Verification* (`SpecVerify MCP`)
  5. *Contradiction Detection* (`TrustScore MCP`)
  6. *Trust Score Computation* (`TrustScore MCP`)
- **Explicit DEMO MODE Labeling:** Persistent warning banners ensure no claims of live execution.
- **Simulated Output Card:** Preview of findings, price ranges, trust metrics, and demo flags.

### 3. Compare (`/compare`)
- **Interactive Multi-Select:** Compare up to 3 sample laptops side-by-side.
- **INR Currency Formatting:** Realistic Indian Rupee pricing clearly tagged as *illustrative sample data*.
- **Comprehensive Spec Tables:** Expandable drawer and responsive side-by-side matrix comparing CPU, GPU, RAM, Display, Battery, and Weight.
- **Filtering & Sorting:** Filter by tags (`premium`, `gaming`, `creator`, etc.) and sort by Price, Trust Score, or Name.

### 4. Evidence (`/evidence`)
- **Evidence Explorer:** Filterable sample evidence records across retailers (Amazon.in, Flipkart, Croma), review sites (Notebookcheck), community forums (Reddit), and official manufacturers.
- **Contradiction Callouts:** Dedicated view isolating flagged pricing differences and unverified claims.
- **Expandable Audit Details:** Inspection view showing source IDs, placeholder URLs, and Phase 2 expectations.

### 5. About (`/about`)
- **Mission Statement:** Explaining the market need for independent product scrutiny.
- **System Architecture Diagram:** Visual layout of User Query → Gemini Orchestrator → 5 MCP Intelligence Servers → Retailer & Review Data Sources.
- **MCP Server Directory:** Specifications and tool signatures for the 5 planned MCP servers (`PriceSpider`, `ReviewSense`, `SpecVerify`, `TrustScore`, `PriceAlert`).
- **Privacy Principles:** Clear statement of zero personal tracking and un-monetized scores.
- **Build Roadmap:** Transparent view of Phase 1 (Completed), Phase 2 (Planned), and Phase 3 (Future).

---

## Getting Started

### Prerequisites
- Node.js 18.18+ or 20+ installed
- npm, yarn, or pnpm

### Installation

```bash
# Clone or navigate to the project directory
cd webtruth

# Install dependencies (if not already installed)
npm install
```

### Running Locally

```bash
# Start the development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build & Verification

```bash
# Typecheck
npx tsc --noEmit

# Lint
npx eslint src --ext .ts,.tsx

# Build for production
npm run build

# Start production server
npm run start
```

---

## Design System

- **Background:** Deep Navy (`#020817` / `rgba(2, 8, 23, 1)`)
- **Primary Accents:** Electric Cyan (`#22d3ee`), Violet (`#8b5cf6`), Neon Green (`#4ade80`)
- **Borders & Panels:** Glassmorphic translucent surfaces with subtle glowing borders (`border-cyan-500/20`)
- **Accessibility:** Fully responsive across mobile, tablet, and desktop viewports; supports `prefers-reduced-motion`.
