# Run My Pool traffic analytics

Run My Pool uses Cloudflare Web Analytics for anonymous page-view, visitor, referrer, device, geography, and Core Web Vitals reporting. It is separate from the application's authenticated lifecycle events.

The beacon is cookie-free and does not receive user IDs, email addresses, pool names, entries, picks, or URL query strings. It automatically observes Next.js client-side navigation.

## Production setup

1. In Cloudflare, open **Analytics & Logs > Web Analytics**.
2. Add a site for `runmypool.net` using the manual JavaScript setup.
3. Copy the site's Web Analytics token. This token is public configuration, not a secret.
4. In the `agsmith/run-my-pool` GitHub repository, open **Settings > Secrets and variables > Actions > Variables**.
5. Create the repository variable `CLOUDFLARE_WEB_ANALYTICS_TOKEN` with the copied token.
6. Run the **Build and Deploy Frontend** workflow or push a frontend change to `main`.
7. Visit several Run My Pool pages, then verify traffic in Cloudflare Web Analytics. Initial results can take a few minutes to appear.

If the variable is absent or blank, the analytics script is not rendered. The frontend Content Security Policy permits only Cloudflare's beacon script and reporting endpoint for this integration.
