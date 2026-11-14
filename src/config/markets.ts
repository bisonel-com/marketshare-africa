import marketsJson from './markets.json';
import categoriesJson from './categories.json';

export type MarketScope = 'worldwide' | 'region' | 'country';
export type GeoCoverage = 'full' | 'worldwide-only' | 'single-country';

export interface CategoryConfig {
  name: string;
  slug: string;
  family: string;
  familySlug: string;
  device: string;
  deviceLabel: string;
  source: string;
  chartKind: string;
  sourcePath?: string;
  sourceName: string;
  sourceHomeUrl: string;
  sourceDataUrl?: string;
  licenceName: string;
  licenceUrl: string;
  derivedLicenceName?: string;
  derivedLicenceUrl?: string;
  metricLabel: string;
  geoCoverage: GeoCoverage;
  geoSlug?: string;
  period: string;
  periodCode: string;
  updateCadence: string;
  methodology: string;
  params?: Record<string, string>;
  soColumn?: string;
}

export interface MarketConfig {
  scope: MarketScope;
  name: string;
  slug: string;
  code: string;
  statcounterRegion: string;
  pathPrefix: string;
}

export const categories = categoriesJson.categories as CategoryConfig[];
export const worldwide = marketsJson.worldwide as MarketConfig;
export const regions = marketsJson.regions as MarketConfig[];
export const countries = marketsJson.countries as MarketConfig[];

export function allMarkets(): MarketConfig[] {
  return [worldwide, ...regions, ...countries];
}

export function findCategory(slug: string): CategoryConfig | undefined {
  return categories.find((c) => c.slug === slug);
}

export function categoriesForMarket(market: MarketConfig): CategoryConfig[] {
  return categories.filter((c) => {
    if (c.geoCoverage === 'full') return true;
    if (c.geoCoverage === 'worldwide-only') return market.scope === 'worldwide';
    if (c.geoCoverage === 'single-country') return market.slug === c.geoSlug;
    return false;
  });
}

export function categoryFamilies(): { family: string; familySlug: string; items: CategoryConfig[] }[] {
  const map = new Map<string, CategoryConfig[]>();
  for (const c of categories) {
    const list = map.get(c.family) || [];
    list.push(c);
    map.set(c.family, list);
  }
  return [...map.entries()].map(([family, items]) => ({
    family,
    familySlug: items[0].familySlug,
    items,
  }));
}
