import type { AgentResponse, Decision, GeoEvent, Health, ModelInfo, PaperPortfolio, PaperPosition, StoredDecision } from "../models/api";

const json = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(path, init);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail ?? `HTTP ${response.status}`);
  return body as T;
};

export const api = {
  modelInfo: () => json<ModelInfo>("/api/v1/ml/model-info"),
  modelRegistry: () => json<any>("/api/v1/models/registry"),
  marketCandles: (symbol: string) => json<any>(`/api/v1/market/candles?symbol=${encodeURIComponent(symbol)}&interval=1h&limit=2`),
  health: () => json<Health>("/api/v1/health"),
  decisions: () => json<StoredDecision[]>("/api/v1/trading/decisions?limit=20"),
  decision: (params: URLSearchParams) => json<Decision>(`/api/v1/trading/decision?${params}`),
  news: () => json<any[]>("/api/v1/news?limit=100"),
  events: () => json<GeoEvent[]>("/api/v1/events?limit=100"),
  research: () => json<Record<string, unknown>>("/api/v1/research/latest"),
  backtest: () => json<Record<string, unknown>>("/api/v1/research/backtest"),
  outcomes: () => json<Record<string, unknown>>("/api/v1/trading/outcomes/summary"),
  paperPortfolio: () => json<PaperPortfolio>("/api/v1/paper/portfolio"),
  paperPositions: () => json<PaperPosition[]>("/api/v1/paper/positions"),
  paperEquity: () => json<Array<{timestamp:string;equity:number}>>("/api/v1/paper/equity"),
  paperMetrics: () => json<Record<string, unknown>>("/api/v1/paper/metrics"),
  agentQuery: (message: string) => json<AgentResponse>("/api/v1/agent/query", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({message})}),
};
