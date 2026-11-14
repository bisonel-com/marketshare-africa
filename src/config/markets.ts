import marketsJson from './markets.json';

export type MarketScope = 'worldwide' | 'region' | 'country';

export interface CategoryConfig {
  name: string;
  slug: string;
  chartKind: 'vendor' | 'browser';
  sourcePath: string;
  methodology: string;
  params: Record<string, string>;
}

export interface MarketConfig {
  scope: MarketScope;
  name: string;
  slug: string;
  code: string;
  statcounterRegion: string;
  pathPrefix: string;
}

export const categories = marketsJson.categories as CategoryConfig[];
export const worldwide = marketsJson.worldwide as MarketConfig;
export const regions = marketsJson.regions as MarketConfig[];
export const countries = marketsJson.countries as MarketConfig[];

export function allMarkets(): MarketConfig[] {
  return [worldwide, ...regions, ...countries];
}

export function findMarketByPathPrefix(pathPrefix: string): MarketConfig | undefined {
  return allMarkets().find((m) => m.pathPrefix === pathPrefix);
}

export function marketHref(market: MarketConfig, categorySlug?: string): string {
  if (categorySlug) return `/${market.pathPrefix}/${categorySlug}/`;
  return `/${market.pathPrefix}/`;
}
