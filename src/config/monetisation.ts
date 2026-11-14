/**
 * Monetisation placeholders: replace before enabling ads or checkout.
 * Scripts and checkout stay inactive while these REPLACE_WITH_* values remain.
 *
 * Payments: Lemon Squeezy is primary (global). Paystack is secondary (African buyers).
 * Both stay placeholders while PRO_CSV_ENABLED is false.
 */

export const ADSENSE_PUB_ID = 'REPLACE_WITH_ADSENSE_PUB_ID';
export const ADSENSE_SLOT_LEADERBOARD = 'REPLACE_WITH_ADSENSE_SLOT_LEADERBOARD';
export const ADSENSE_SLOT_IN_TABLE = 'REPLACE_WITH_ADSENSE_SLOT_IN_TABLE';
export const ADSENSE_SLOT_ANCHOR = 'REPLACE_WITH_ADSENSE_SLOT_ANCHOR';

/** Primary checkout (global). */
export const LEMON_SQUEEZY_STORE_ID = 'REPLACE_WITH_LEMON_SQUEEZY_STORE_ID';
export const LEMON_SQUEEZY_PRODUCT_ID = 'REPLACE_WITH_LEMON_SQUEEZY_PRODUCT_ID';

/** Secondary checkout for African buyers. */
export const PAYSTACK_PUBLIC_KEY = 'REPLACE_WITH_PAYSTACK_PUBLIC_KEY';

/** Plausible domain or Cloudflare beacon token. Empty / placeholder = loads nothing. */
export const ANALYTICS_DOMAIN = 'REPLACE_WITH_ANALYTICS_DOMAIN';
export const ANALYTICS_PROVIDER: 'none' | 'plausible' | 'cloudflare' = 'none';

/**
 * Pro CSV export paywall: OFF until licence question is resolved.
 * When false: ProPaywallModal and /pro are coming-soon only; no CSV, checkout, or localStorage unlock.
 */
export const PRO_CSV_ENABLED = false;

export function isPlaceholder(value: string): boolean {
  return !value || value.startsWith('REPLACE_WITH_');
}

export function adsEnabled(): boolean {
  return !isPlaceholder(ADSENSE_PUB_ID);
}

export function analyticsEnabled(): boolean {
  return ANALYTICS_PROVIDER !== 'none' && !isPlaceholder(ANALYTICS_DOMAIN);
}
