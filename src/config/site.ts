/**
 * Site URL and base path.
 * SITE_URL is always the canonical public origin (custom domain).
 * SITE_BASE is set via env (build-time) for asset/routing prefixes.
 * Default '/' for the custom domain. Until DNS is live, GitHub Actions sets
 * SITE_BASE from vars.PAGES_BASE (fallback '/marketshare-africa') so the
 * github.io preview keeps working under the subpath.
 *
 * Canonical, OG, sitemap locs, and JSON-LD always use SITE_URL without the
 * temporary Pages subpath.
 *
 * Brand rename: change SITE_NAME (and SITE_TAGLINE if needed) in one place.
 */
export const SITE_NAME = 'GMarketShare';
export const SITE_TAGLINE = 'Global Market Share';
export const SITE_URL = 'https://xmarketshare.com';
export const SITE_BASE = (import.meta.env.SITE_BASE as string | undefined) || '/';

export const SITE_DESCRIPTION =
  'Market share rankings worldwide and by country, sourced from Statcounter Global Stats.';

export const SOCIAL = {
  x: 'REPLACE_WITH_GMARKETSHARE_X_HANDLE',
  linkedin: 'REPLACE_WITH_GMARKETSHARE_LINKEDIN',
  github: 'bisonel-com/marketshare-africa',
};

/** Canonical origin (custom domain). No temporary Pages base. */
export function siteOrigin(): string {
  return SITE_URL.replace(/\/$/, '');
}

/** Join a path with the Astro base (for in-app links and assets). */
export function withBase(path: string): string {
  const base = SITE_BASE.replace(/\/$/, '');
  const clean = path.startsWith('/') ? path : `/${path}`;
  if (clean === '/') return base ? `${base}/` : '/';
  return `${base}${clean}`;
}

/** Absolute canonical URL for a site path (no temporary Pages base). */
export function canonicalUrl(path: string): string {
  const clean = path.startsWith('/') ? path : `/${path}`;
  if (clean === '/') return `${siteOrigin()}/`;
  const withSlash = clean.endsWith('/') ? clean : `${clean}/`;
  return `${siteOrigin()}${withSlash}`;
}
