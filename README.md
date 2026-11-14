# Global Market Share

Market share rankings worldwide and by country, sourced from [Statcounter Global Stats](https://gs.statcounter.com/). Built with Astro. Repo: `bisonel-com/marketshare-africa`.

Brand name lives in `src/config/site.ts` as `SITE_NAME` (one-line rename later if needed).

**Canonical site:** https://xmarketshare.com  
**GitHub Pages preview (until DNS is live):** https://bisonel-com.github.io/marketshare-africa/

## Quick start

```bash
npm ci
SITE_BASE=/marketshare-africa npm run build   # matches current Pages deploy
npm run preview
```

Open `http://localhost:4321/marketshare-africa/`.

For local custom-domain simulation:

```bash
SITE_BASE=/ npm run build && npm run preview
```

## Markets (config-driven)

All markets and categories live in `src/config/markets.json` (imported by Astro and the Python scraper). Adding a market needs a JSON entry only.

- **Worldwide** (`ww`)
- **Regions:** Africa, Asia, Europe, North America, South America, Oceania
- **Countries:** US, UK, India, Brazil, Germany, France, Japan, Indonesia, Mexico, Nigeria, South Africa, Kenya, Egypt, Canada, Australia, Spain, Italy, Turkey, Saudi Arabia, Philippines
- **Categories:** Mobile Phones (vendor), Web Browsers

URL scheme:

- `/worldwide/{category}/` and hub `/worldwide/`
- `/region/{region}/{category}/` and hub `/region/{region}/`
- `/{country}/{category}/` and hub `/{country}/`

## Scrape data

```bash
pip install -r scripts/requirements.txt
python scripts/scrape_marketshare.py
```

- Real monthly Statcounter CSVs only; failed fetches are skipped and reported.
- `OPENAI_API_KEY` optional; without it, deterministic fact-only summaries/FAQs are used.
- Cron: `.github/workflows/scrape-data.yml` (`0 6 3 * *` + `workflow_dispatch`). After a bot commit it dispatches `deploy.yml` (token pushes do not trigger other workflows).

## Deploy & base path

`.github/workflows/deploy.yml` builds with:

```yaml
SITE_BASE: ${{ vars.PAGES_BASE != '' && vars.PAGES_BASE || '/marketshare-africa' }}
```

`public/CNAME` contains `xmarketshare.com`. Canonical URLs, OG, sitemap, robots.txt, and JSON-LD use `https://xmarketshare.com`.

### Switch to the custom domain (one ops step)

1. In GitHub Pages settings, set the custom domain to `xmarketshare.com` and wait for DNS/TLS.
2. Set repository variable `PAGES_BASE` to `/` (or empty once you change the workflow default).
3. Redeploy. No code change required beyond that variable.

## Placeholders (inactive until replaced)

`src/config/monetisation.ts`:

| Constant | Notes |
| --- | --- |
| `REPLACE_WITH_ADSENSE_PUB_ID` (+ slots) | Ad scripts do not load; CLS-safe empty slots still render |
| `REPLACE_WITH_LEMON_SQUEEZY_*` | Primary checkout (global); unused while Pro is off |
| `REPLACE_WITH_PAYSTACK_PUBLIC_KEY` | Secondary checkout for African buyers; unused while Pro is off |
| `REPLACE_WITH_ANALYTICS_DOMAIN` | Analytics loads nothing; `window.msaTrack` is a safe no-op |
| `PRO_CSV_ENABLED` | `false` (Pro is coming-soon only) |
| `REPLACE_WITH_GLOBALMARKETSHARE_X_HANDLE` / LinkedIn | Social placeholders in `src/config/site.ts` |

`public/ads.txt` uses the AdSense publisher placeholder for xmarketshare.com.

## Licence

- **Source data:** Statcounter Global Stats (https://gs.statcounter.com), licensed [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/).
- **Derived rankings** on this site are shared under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), relying on BY-SA 3.0 section 4(b), which permits adaptations under a later version.

See `/licence/` on the site and `src/config/licence.ts`. © Global Market Share. Pro CSV remains off (`PRO_CSV_ENABLED=false`).
