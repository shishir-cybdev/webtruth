import type {
  BackendHealthResponse,
  InvestigationCreateRequest,
  InvestigationListResponse,
  InvestigationResponse,
  InvestigationSSEEvent,
  MCPHealthResponse,
} from "@/types/api";

const DEFAULT_PRODUCTION_API_URL = "https://webtruth.onrender.com";

function resolveApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim().replace(/\/$/, "");
  if (configured) {
    return configured;
  }
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host !== "localhost" && host !== "127.0.0.1") {
      return DEFAULT_PRODUCTION_API_URL;
    }
  } else if (process.env.NODE_ENV === "production") {
    return DEFAULT_PRODUCTION_API_URL;
  }
  return "http://127.0.0.1:8000";
}

export const API_BASE_URL = resolveApiBaseUrl();

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(message: string, status = 0, detail = "") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail || message;
  }
}

async function fetchWithTimeout<T>(
  path: string,
  options: RequestInit & { timeoutMs?: number } = {}
): Promise<T> {
  const { timeoutMs = 15000, ...fetchOptions } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(fetchOptions.headers || {}),
      },
    });

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const errJson = await response.json();
        detail = errJson.detail || errJson.message || JSON.stringify(errJson);
      } catch {
        // ignore JSON parse error on error response
      }
      throw new ApiError(
        `API Error (${response.status}): ${detail}`,
        response.status,
        detail
      );
    }

    return (await response.json()) as T;
  } catch (err) {
    if (err instanceof ApiError) {
      throw err;
    }
    if (err instanceof Error && err.name === "AbortError") {
      throw new ApiError(
        `Request timed out after ${timeoutMs / 1000}s while contacting ${API_BASE_URL}.`,
        408,
        "Request timeout"
      );
    }
    throw new ApiError(
      `Unable to reach WebTruth backend at ${API_BASE_URL}. Ensure the FastAPI server is running.`,
      0,
      err instanceof Error ? err.message : String(err)
    );
  } finally {
    clearTimeout(timer);
  }
}

export async function checkBackendHealth(): Promise<BackendHealthResponse> {
  return fetchWithTimeout<BackendHealthResponse>("/api/health", {
    method: "GET",
    timeoutMs: 8000,
  });
}

export async function checkMcpHealth(): Promise<MCPHealthResponse> {
  return fetchWithTimeout<MCPHealthResponse>("/api/health/mcp", {
    method: "GET",
    timeoutMs: 30000, // Launching 4 stdio subprocesses can take a few seconds
  });
}

export async function createInvestigation(
  payload: InvestigationCreateRequest
): Promise<InvestigationResponse> {
  return fetchWithTimeout<InvestigationResponse>("/api/investigations", {
    method: "POST",
    body: JSON.stringify(payload),
    timeoutMs: 15000,
  });
}

export async function getInvestigation(
  investigationId: string
): Promise<InvestigationResponse> {
  return fetchWithTimeout<InvestigationResponse>(
    `/api/investigations/${encodeURIComponent(investigationId)}`,
    {
      method: "GET",
      timeoutMs: 12000,
    }
  );
}

export async function listInvestigations(
  limit = 20,
  offset = 0
): Promise<InvestigationListResponse> {
  return fetchWithTimeout<InvestigationListResponse>(
    `/api/investigations?limit=${limit}&offset=${offset}`,
    {
      method: "GET",
      timeoutMs: 12000,
    }
  );
}

export function subscribeToInvestigationEvents(
  investigationId: string,
  callbacks: {
    onEvent: (event: InvestigationSSEEvent) => void;
    onError?: (error: Event) => void;
    onOpen?: () => void;
  }
): () => void {
  const url = `${API_BASE_URL}/api/investigations/${encodeURIComponent(investigationId)}/events`;
  const source = new EventSource(url);

  source.onopen = () => {
    callbacks.onOpen?.();
  };

  source.onmessage = (msg) => {
    try {
      const parsed = JSON.parse(msg.data) as InvestigationSSEEvent;
      callbacks.onEvent(parsed);
    } catch {
      // Ignore malformed heartbeat or non-JSON comment frames
    }
  };

  source.onerror = (err) => {
    callbacks.onError?.(err);
  };

  return () => {
    source.close();
  };
}
