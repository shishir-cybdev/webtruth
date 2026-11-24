// Shared types for WebTruth

export interface Product {
  id: string;
  name: string;
  brand: string;
  category: string;
  price: number; // INR
  image: string;
  specs: Record<string, string>;
  score: number; // 0-100
  badge?: string;
  tags: string[];
}

export interface EvidenceRecord {
  id: string;
  source: string;
  sourceType: "retailer" | "review" | "forum" | "official" | "unknown";
  url: string;
  claimedPrice: number;
  verifiedAt: string | null;
  confidence: number; // 0-100
  contradiction?: string;
  status: "verified" | "unverified" | "contradicted" | "pending";
  excerpt: string;
}

export interface InvestigationStep {
  id: string;
  label: string;
  description: string;
  status: "pending" | "running" | "complete" | "error";
  mcpServer: string;
  durationMs?: number;
}

export interface SearchQuery {
  query: string;
  category?: string;
  timestamp: Date;
}

export interface MCPServer {
  id: string;
  name: string;
  description: string;
  status: "planned" | "prototype" | "active";
  tools: string[];
  icon: string;
}
