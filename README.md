# DAMVerse — LinkedIn Ad Performance Portal

A single-file, zero-backend portal for turning LinkedIn Campaign Manager CSV exports into a
management-ready performance report. Everything lives in `index.html` — no build step, no server.

## How it works

1. **Landing page** — type a campaign name (existing names autofill) or click an existing
   campaign card. A cross-campaign snapshot table compares spend, CTR, CPC, leads, and CPL
   when you have more than one campaign.
2. **Google Drive sync** — all data comes in via the **⟳ Fetch data from Drive** button,
   which reads the LinkedIn CSVs in the configured Drive folder (details below). Export with
   a **daily time breakdown** (Analyze → Export → CSV) so the trend chart has data.
   Re-fetching is safe: rows for the same dates are overwritten, new dates are appended.
3. **Report** — KPI cards, conversion funnel, auto-generated "what management should know"
   insights (benchmarked against LinkedIn B2B norms), and a date-wise trend chart with a
   metric selector (impressions / clicks / CTR / spend / leads / CPL).

Data is stored in the browser's `localStorage`. Use **Export all data** / **Import data**
on the landing page to back up or move data between machines.

## Hosting on GitHub Pages

```bash
git init
git add .
git commit -m "DAMVerse ad performance portal"
gh repo create damverse-portal --private --source=. --push
```

Then on GitHub: **Settings → Pages → Deploy from branch → main / (root)**.
Your portal will be live at `https://<username>.github.io/damverse-portal/`.

(Any static host works: Netlify Drop, Vercel, Cloudflare Pages, or just opening
`index.html` from disk.)

## Google Drive sync (Fetch data button)

The landing page's **⟳ Fetch data from Drive** button reads every CSV in a Drive folder and
updates the matching campaigns automatically. Rows are split by the file's **Campaign Name
column**, so a single account-level export covering several campaigns updates each one —
you can replace one file, drop in separately named exports, or point an automation
(e.g. Zapier delivering LinkedIn's scheduled report emails into the folder) at it; all work,
even mixed. Already-imported files (same modified time) are skipped.

One-time setup by the admin (~3 minutes) — after this, **visitors need zero setup**:

1. **Share the folder**: in Google Drive, right-click the folder → Share → "Anyone with the link — Viewer".
2. **Create a free API key**: go to [console.cloud.google.com](https://console.cloud.google.com) →
   create a project (any name) → **APIs & Services → Library → Google Drive API → Enable** →
   **APIs & Services → Credentials → Create credentials → API key**.
3. **Restrict the key** (required before committing it):
   - *API restrictions* → Restrict key → **Google Drive API** only
   - *Website restrictions* → add your portal URL, e.g. `https://<username>.github.io/*`
4. Paste the key into the `DRIVE_DEFAULT_KEY` constant near the top of the script in
   `index.html` and push. Restricted this way, the key can only read link-shared files and
   only from your portal's domain, so it is safe to publish (this is Google's intended
   pattern for browser keys, same as embedded Maps keys).

Anyone viewing the portal then just clicks **⟳ Fetch data from Drive**. The **⚙ Configure**
button remains as a per-browser override for the key or folder ID (stored in localStorage only).

## Alerts

The bell icon in the header shows a badge when any campaign trips a threshold:

- **Spend** approaching (within $10 of) or crossing each $100 mark
- **CPL** above $50

Alerts can be dismissed individually or all at once; a dismissed alert only returns when the
next milestone is crossed. Thresholds live in one place in `index.html`
(`const THRESHOLDS = { budgetStep: 100, budgetWarnWithin: 10, cplLimit: 50 }`).

## Daily workflow

1. Get the LinkedIn CSV (daily breakdown, full date range) into the Drive folder — manually,
   or automatically via Zapier delivering LinkedIn's scheduled report emails.
2. Open the portal → **⟳ Fetch data from Drive**. Every campaign found in the files updates.
3. Share the URL with management; they click Fetch, then a campaign card, to see reports.

`sample-data/sample-linkedin-export.csv` is a realistic example export — drop it in the Drive
folder to demo the portal.

## CSV compatibility

The parser handles LinkedIn's export quirks: preamble rows before the header, comma/tab/semicolon
delimiters, UTF-16 encoded files, quoted fields, `$`/`%`/thousands separators, and both daily and
summary-only exports. Column names are matched fuzzily (e.g. "Total Spent" / "Amount Spent" / "Spend").
