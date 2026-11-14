import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import sitemap from '@astrojs/sitemap';

// SITE_URL must stay in sync with src/config/site.ts (custom domain).
// SITE_BASE comes from env so github.io previews can use /marketshare-africa
// until DNS for the custom domain is live.
const SITE_URL = 'https://xmarketshare.com';
const SITE_BASE = process.env.SITE_BASE || '/';
const baseNorm = SITE_BASE.replace(/\/$/, '') || '';

export default defineConfig({
  site: SITE_URL,
  base: SITE_BASE,
  output: 'static',
  vite: {
    define: {
      'import.meta.env.SITE_BASE': JSON.stringify(SITE_BASE),
    },
  },
  integrations: [
    tailwind({ applyBaseStyles: false }),
    sitemap({
      filter: (page) => !page.includes('/pro'),
      // Canonical sitemap locs always use the custom domain root paths, even
      // when the build base is temporarily /marketshare-africa for github.io.
      serialize(item) {
        if (baseNorm && item.url.includes(`${SITE_URL}${baseNorm}`)) {
          item.url = item.url.replace(`${SITE_URL}${baseNorm}`, SITE_URL);
        }
        return item;
      },
    }),
  ],
});
