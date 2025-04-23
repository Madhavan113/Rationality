// General market types
export interface Market {
  id: string;
  name: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

// Leaderboard types
export interface LeaderboardEntry {
  trader_id: string;
  trader_name: string;
  market_id: string;
  score: number;
  position: number;
  timestamp: string;
}

export interface Leaderboard {
  market_id: string;
  timestamp: string;
  entries: LeaderboardEntry[];
}

// Alert types
export interface AlertRule {
  id?: string;
  name: string;
  market_id: string;
  email: string;
  threshold: number;
  condition: "above" | "below";
  created_at?: string;
}

// TruePrice types
export interface TruePriceData {
  market_id: string;
  timestamp: string;
  value: number;
  mid_price: number;
}

// Rationality types
export interface Order {
  makerAddress: string;
  price: number;
  size: number;
  side: "BUY" | "SELL";
  outcome: string;
  timestamp: number;
}

export interface Trade {
  makerAddress: string;
  price: number;
  size: number;
  outcome: string;
  timestamp: number;
}

export interface RawInputs {
  orders?: Order[];
  trades?: Trade[];
}

export interface RationalityMetrics {
  marketId: string;
  computedAt: number;
  overallScore: number;
  perTraderScore: Record<string, number>;
  rawInputs?: RawInputs;
} 