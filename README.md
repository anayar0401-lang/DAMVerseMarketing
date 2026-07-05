# DAMVerse — LinkedIn Ad Performance Portal

A single-file, zero-backend portal for turning LinkedIn Campaign Manager CSV exports into a
management-ready performance report. Everything lives in `index.html` — no build step, no server.

## How it works

1. **Landing page** — type a campaign name (existing names autofill) or click an existing
   campaign card. A cross-campaign snapshot table compares spend, CTR, CPC, leads, and CPL
   when you have more than one campaign.
2. **Upload screen** — drop in the latest CSV exported from LinkedIn Campaign Manager
   (Analyze → Export → CSV, **daily time breakdown** recommended). Re-uploading is safe:
   rows for the same dates are overwritten, new dates are appended.
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
updates the matching campaigns automatically — the campaign name is read from inside each file,
so you can either keep replacing one file or add separately named exports; both work, even mixed.
Already-imported files (same modified time) are skipped.

One-time setup (~2 minutes):

1. **Share the folder**: in Google Drive, right-click the folder → Share → "Anyone with the link — Viewer".
2. **Create a free API key**: go to [console.cloud.google.com](https://console.cloud.google.com) →
   create a project (any name) → **APIs & Services → Library → Google Drive API → Enable** →
   **APIs & Services → Credentials → Create credentials → API key**.
   Recommended: restrict the key to the Google Drive API, and add your GitHub Pages URL as an
   allowed HTTP referrer.
3. In the portal, click **⚙ Configure**, paste the API key, and confirm the folder ID
   (pre-filled with the DAMVerse reports folder). The key is stored only in that browser's
   localStorage — it is never written into this repo.

Each person viewing the portal (e.g. management) enters the key once in their own browser;
after that, one click on Fetch pulls the latest numbers.

## Alerts

The bell icon in the header shows a badge when any campaign trips a threshold:

- **Spend** approaching (within $10 of) or crossing each $100 mark
- **CPL** above $50

Alerts can be dismissed individually or all at once; a dismissed alert only returns when the
next milestone is crossed. Thresholds live in one place in `index.html`
(`const THRESHOLDS = { budgetStep: 100, budgetWarnWithin: 10, cplLimit: 50 }`).

## Daily workflow

1. In LinkedIn Campaign Manager, export the campaign's CSV (daily breakdown, full date range).
2. Open the portal → click the campaign → **Upload new CSV** → drop the file.
3. Share the URL with management; they click a campaign card to see the report.

`sample-data/sample-linkedin-export.csv` is a realistic example export you can use to demo the portal.

## CSV compatibility

The parser handles LinkedIn's export quirks: preamble rows before the header, comma/tab/semicolon
delimiters, UTF-16 encoded files, quoted fields, `$`/`%`/thousands separators, and both daily and
summary-only exports. Column names are matched fuzzily (e.g. "Total Spent" / "Amount Spent" / "Spend").
