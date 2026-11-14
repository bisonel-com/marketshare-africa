export type MarketScope = 'worldwide' | 'region' | 'country';

export interface RankingRow {
  rank: number;
  brand: string;
  parentCompany: string;
  sharePercent: number;
  yoyChange: number | null;
  segment: string;
  highlight: boolean;
}

export interface FaqItem {
  question: string;
  answer: string;
}

export interface MarketData {
  slug: string;
  scope: MarketScope;
  market: string;
  marketSlug: string;
  marketCode: string;
  category: string;
  categorySlug: string;
  period: string;
  lastUpdated: string;
  sourceName: string;
  sourceUrl: string;
  methodologyNote: string;
  aiSummary: string;
  faqs: FaqItem[];
  rankings: RankingRow[];
  country?: string;
  countryCode?: string;
}
