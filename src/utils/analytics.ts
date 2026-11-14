/** Safe no-op analytics helper. Loads nothing until ANALYTICS_* is configured. */

export type AnalyticsEvent =
  | { name: 'filter_change'; props: { country: string; category: string } }
  | { name: 'cite_data_click'; props: { slug: string } }
  | { name: 'pro_modal_open'; props: { trigger: string; slug: string } }
  | { name: 'pro_checkout_complete'; props: { plan: string; currency: string } };

declare global {
  interface Window {
    msaTrack?: (event: AnalyticsEvent['name'], props?: Record<string, string>) => void;
    plausible?: (event: string, options?: { props?: Record<string, string> }) => void;
  }
}

export const ANALYTICS_HELPER_INLINE = `
window.msaTrack = function (name, props) {
  try {
    if (typeof window.plausible === 'function') {
      window.plausible(name, props ? { props: props } : undefined);
    }
  } catch (e) {}
};
`;
