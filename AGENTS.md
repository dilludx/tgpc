# TGPC v2 — Architecture & Context

> **IMPORTANT:** Before making ANY code change to `v2/`, read this document fully and update the Change Log and Status sections at the bottom when done. This file is the single source of truth for context across sessions.
>
> For the full repo overview (Python pipeline, current frontend, deployment), see `ARCHITECTURE.md`.

## Stack
- **Framework:** SvelteKit 5 + Cloudflare adapter (`@sveltejs/adapter-cloudflare`)
- **Styling:** Tailwind CSS v4
- **Runtime:** Node 20+
- **Database:** Supabase (same project, same anon key)
- **Hosting:** Cloudflare Pages (deployed alongside current site)

## Project Structure
```
v2/
├── src/
│   ├── routes/
│   │   ├── +layout.svelte        # Shared header, footer, connection status, stats
│   │   ├── +page.svelte          # Search (desktop table + mobile cards)
│   │   ├── notice/+page.svelte   # Notices page
│   │   ├── dispatch/+page.svelte # Dispatch PDF list
│   │   └── api/
│   │       ├── dispatch/+server.ts  # R2 listing proxy
│   │       └── notice/+server.ts    # Static notice JSON
│   ├── lib/
│   │   ├── supabase.ts           # Supabase client singleton
│   │   ├── types.ts              # Shared types (PharmacistRecord, Notice, etc.)
│   │   └── utils.ts              # Formatting helpers (escapeHtml, dates, etc.)
│   └── app.html
├── static/
│   ├── pdf.png
│   ├── excel.png
│   ├── og-image.png
│   └── favicon.svg
├── svelte.config.js
├── tailwind.config.js
├── vite.config.ts
└── package.json
```

## Route Map
| Path | Description |
|---|---|
| `/` | Search page — desktop table + mobile cards, responsive |
| `/notice` | Notices & circulars table, year tabs, search |
| `/dispatch` | Dispatch PDF grid, search, year tabs |
| `/api/dispatch` | JSON — lists PDFs from Cloudflare R2 |
| `/api/notice` | Static JSON — notice data from `notice.json` |

## Design System (ported from current site)
- **Green:** `#00cc66` — brand, primary buttons, active filters, connected status
- **Red:** `#ef4444` — "Rx" brand text, PharmD badges, dispatch link
- **Gray:** `#808080` / `#9ca3af` — secondary text, footer, "Registry" brand text
- **Text:** `#1a1a1a` — primary body text
- **Background:** `#f8f9fa` — page and section backgrounds
- **Borders:** `#e5e7eb` / `#f4f4f5` — section and table borders

### Category Badges
| Category | Background | Text |
|---|---|---|
| BPharm | `#dcfce7` | `#166534` |
| DPharm | `#fef9c3` | `#854d0e` |
| MPharm | `#ede9fe` | `#5b21b6` |
| PharmD | `#fecaca` | `#991b1b` |
| QC | `#dbeafe` | `#1e40af` |
| QP | `#fed7aa` | `#9a3412` |

- **Font:** `-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif`
- **Border radius:** `8px` (sections), `999px` (buttons/chips), `6px` (badges)

## Data Flow
### Search
1. Supabase client initialized with `TGPC_CONFIG` (same anon key approach)
2. User types ≥3 chars → `SELECT registration_number, name, father_name, category FROM rx WHERE registration_number ILIKE %q% OR name ILIKE %q% OR father_name ILIKE %q% LIMIT 100000`
3. Results sorted client-side by custom prefix order: `TS → TG → TSDR → TGDR`, then numeric
4. Filtered by category chip, paginated (50/page desktop, 25/page mobile)
5. Export: jsPDF for PDF, Blob download for CSV

### Stats
1. Show cached stats from `localStorage` immediately
2. Fetch fresh stats via Supabase RPC `get_rx_stats`
3. Update display if totals differ

### Connection Status
1. On load: "Busy" (connecting state)
2. After successful query: "Live" with current date + live clock
3. On error: "Offline"

### Realtime Polling
- Fetches `last_sync` from `metadata` table every 5 minutes
- If changed, shows notification and auto-refreshes search + stats

## Notices Page
- Fetches from `/api/notice` endpoint
- Data source: `static/notice.json` (copied from current `docs/notice.json`)
- Sort by date descending, filtered by year tabs + search

## Dispatch Page
- Fetches from `/api/dispatch` endpoint
- Worker proxy lists objects from `DISPATCH` R2 bucket with prefix `dispatch/`
- Parses filenames (`DLDDMMYYYY.pdf`), sorts by date descending
- Filtered by year tabs + search
- Links to public R2 URL for download

## API Routes
### `/api/notice`
- Returns `notice.json` as static JSON
- Workers `+server.ts` imports the JSON and returns it

### `/api/dispatch`
- Requires Cloudflare binding `DISPATCH` (R2 bucket) in production
- In dev, returns sample/fallback data
- Lists objects, returns `[{name, size}]`

## Build & Deploy
```bash
cd v2
npm install
npm run dev          # Local preview at localhost:5173
npm run build        # Production build to .svelte-kit/cloudflare
npm run preview      # Preview production build locally
```

### Coexistence with current site
- Current site: `docs/` deployed on Cloudflare Pages as main site
- v2: deployed via branch preview or subdirectory
- `_worker.js` updated at final switch to route traffic

## Future Considerations
- Search pagination: current limit is 100000, consider server-side pagination if performance becomes an issue
- Enrichment data: could add a "detail view" for individual pharmacist records
- Search sharing: URL query parameters for shareable search results

## Change Log
| Date | Change |
|---|---|
| _(first entry on creation)_ | Initial project scaffold and this document |

## Status
- [ ] Scaffold SvelteKit + Tailwind + Cloudflare adapter
- [ ] Build shared layout (header, footer, status, stats)
- [ ] Build search page (desktop table + mobile cards)
- [ ] Implement Supabase search logic
- [ ] Implement filter chips + pagination
- [ ] Implement PDF/CSV export
- [ ] Build notices page
- [ ] Build dispatch page
- [ ] Add API routes
- [ ] Finalize Worker
- [ ] Review on localhost
- [ ] Deploy to preview URL
- [ ] Swap to production
