import type { MarketData } from './types';

const modules = {
  ...import.meta.glob('../data/worldwide/*.json', { eager: true }),
  ...import.meta.glob('../data/region/*/*.json', { eager: true }),
  ...import.meta.glob('../data/*/*.json', { eager: true }),
} as Record<string, { default: MarketData }>;

export function getAllMarketData(): MarketData[] {
  return Object.values(modules)
    .map((m) => m.default)
    .filter((d) => d && d.slug && Array.isArray(d.rankings) && d.scope)
    .sort((a, b) => a.slug.localeCompare(b.slug));
}

export function getMarketDataBySlug(slug: string): MarketData | undefined {
  return getAllMarketData().find((d) => d.slug === slug);
}

export function getDataForMarketPath(pathPrefix: string): MarketData[] {
  return getAllMarketData().filter((d) => d.slug.startsWith(`${pathPrefix}/`));
}

export function getPublishedData(): MarketData[] {
  // Include insufficient-data stubs so geo pages can show empty state
  return getAllMarketData();
}

export function getCategoriesFromData(): { slug: string; name: string }[] {
  const map = new Map<string, { slug: string; name: string }>();
  for (const d of getAllMarketData()) {
    if (!map.has(d.categorySlug)) {
      map.set(d.categorySlug, { slug: d.categorySlug, name: d.category });
    }
  }
  return [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
}
