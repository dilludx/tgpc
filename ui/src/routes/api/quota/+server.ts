import { json } from '@sveltejs/kit';
import type { QuotaReport, ServiceQuota } from '$lib/types';

const FREE_TIER: Record<string, Record<string, number>> = {
  supabase: { storage_size_gb: 1.0 },
  r2: { storage_gb: 10.0, class_a_ops: 1_000_000, class_b_ops: 10_000_000 },
  pages: { builds: 500 },
  resend: { emails_per_day: 100, emails_per_month: 3000 },
};

function pct(used: number | null, limit: number | null): string {
  if (used === null || limit === null || limit === 0) return '-';
  return (used / limit * 100).toFixed(1) + '%';
}

function fmt(n: number | null): string {
  if (n === null) return '?';
  return n.toLocaleString('en-IN', { maximumFractionDigits: 2 });
}

function hms(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${h}h ${m}m`;
}

async function checkSupabase(env: Record<string, string>): Promise<ServiceQuota> {
  const items: ServiceQuota['items'] = [];
  const pat = env['SUPABASE_PAT'];
  const url = env['SUPABASE_URL'];
  const key = env['SUPABASE_SECRET_KEY'];
  if (!pat || !url) return { name: 'Supabase', items, error: 'Missing SUPABASE_PAT or SUPABASE_URL' };

  const ref = url.match(/https:\/\/([^.]+)\.supabase\.co/)?.[1];
  if (!ref) return { name: 'Supabase', items, error: 'Bad SUPABASE_URL' };

  try {
    const aR = await fetch(`https://api.supabase.com/v1/projects/${ref}/analytics/endpoints/usage.api-requests-count`, {
      headers: { Authorization: `Bearer ${pat}` }
    });
    if (aR.ok) {
      const d: any = await aR.json();
      const count = d.result?.[0]?.count;
      items.push({ label: 'API Requests', used: fmt(count), limit: null, pct: '-' });
    } else {
      items.push({ label: 'API Requests', used: 'Error ' + aR.status, limit: '', pct: '-' });
    }
  } catch { items.push({ label: 'API', used: 'Error', limit: '', pct: '-' }); }

  try {
    if (key) {
      const stR = await fetch(`${url}/rest/v1/rpc`, {
        method: 'POST', headers: { apikey: key, Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' }
      });
      if (!stR.ok) {
        items.push({ label: 'DB/Storage', used: 'RPC unavailable', limit: '', pct: '-' });
      }
    }
  } catch {}

  try {
    const sqlR = await fetch(`https://api.supabase.com/v1/projects/${ref}/database/query`, {
      method: 'POST', headers: { Authorization: `Bearer ${pat}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: "SELECT (sum(pg_database_size(datname)) / 1073741824.0)::numeric(10,4) as size_gb FROM pg_database" })
    });
    if (sqlR.ok) {
      const d: any = await sqlR.json();
      const gb = parseFloat(d[0]?.size_gb);
      items.push({ label: 'Database', used: fmt(gb) + ' GB', limit: null, pct: '-' });
    }

    const stR = await fetch(`https://api.supabase.com/v1/projects/${ref}/database/query`, {
      method: 'POST', headers: { Authorization: `Bearer ${pat}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: "SELECT (sum((metadata->>'size')::int) / (1024.0*1024.0*1024.0))::numeric(10,4) as size_gb FROM storage.objects" })
    });
    if (stR.ok) {
      const d: any = await stR.json();
      const gb = parseFloat(d[0]?.size_gb) || 0;
      items.push({ label: 'Storage', used: fmt(gb) + ' GB', limit: fmt(FREE_TIER.supabase.storage_size_gb) + ' GB', pct: pct(gb, FREE_TIER.supabase.storage_size_gb) });
    }
  } catch {}

  return { name: 'Supabase', items };
}

async function checkR2(env: Record<string, string>): Promise<ServiceQuota> {
  const items: ServiceQuota['items'] = [];
  const token = env['CLOUDFLARE_API_TOKEN'];
  const account_id = env['CLOUDFLARE_ACCOUNT_ID'];
  if (!token || !account_id) return { name: 'Cloudflare R2', items, error: 'Missing CLOUDFLARE_API_TOKEN or CLOUDFLARE_ACCOUNT_ID' };

  try {
    const r = await fetch(`https://api.cloudflare.com/client/v4/accounts/${account_id}/r2/buckets/tgpc/usage`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (r.ok) {
      const d: any = await r.json();
      const bytes = parseInt(d.result?.payloadSize) || 0;
      const gb = bytes / 1073741824;
      items.push({ label: 'Storage', used: fmt(gb) + ' GB', limit: fmt(FREE_TIER.r2.storage_gb) + ' GB', pct: pct(gb, FREE_TIER.r2.storage_gb) });
      items.push({ label: 'Objects', used: fmt(d.result?.objectCount), limit: null, pct: '-' });
    }

    const now = new Date().toISOString();
    const monthStart = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString();
    const gql = {
      query: `query { viewer { accounts(filter: {accountTag: "${account_id}"}) { r2OperationsAdaptiveGroups(limit: 10000, filter: { datetime_geq: "${monthStart}", datetime_leq: "${now}" }) { sum { requests } dimensions { actionType } } } } }`
    };
    const gqlR = await fetch(`https://api.cloudflare.com/client/v4/graphql`, {
      method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(gql)
    });
    if (gqlR.ok) {
      const gd: any = await gqlR.json();
      const groups = gd?.data?.viewer?.accounts?.[0]?.r2OperationsAdaptiveGroups || [];
      const classA = new Set(['PutObject', 'DeleteObject', 'ListObjects', 'CreateMultipartUpload', 'PutBucket', 'DeleteBucket', 'HeadBucket']);
      const classB = new Set(['GetObject', 'HeadObject']);
      let a = 0, b = 0;
      for (const g of groups) {
        const t = g.dimensions?.actionType;
        const c = g.sum?.requests || 0;
        if (classA.has(t)) a += c;
        else if (classB.has(t)) b += c;
      }
      items.push({ label: 'Class A Ops', used: fmt(a), limit: fmt(FREE_TIER.r2.class_a_ops), pct: pct(a, FREE_TIER.r2.class_a_ops) });
      items.push({ label: 'Class B Ops', used: fmt(b), limit: fmt(FREE_TIER.r2.class_b_ops), pct: pct(b, FREE_TIER.r2.class_b_ops) });
    }
  } catch { items.push({ label: 'API', used: 'Error', limit: '', pct: '-' }); }

  return { name: 'Cloudflare R2', items };
}

async function checkPages(env: Record<string, string>): Promise<ServiceQuota> {
  const items: ServiceQuota['items'] = [];
  const token = env['CLOUDFLARE_API_TOKEN'];
  const account_id = env['CLOUDFLARE_ACCOUNT_ID'];
  if (!token || !account_id) return { name: 'Cloudflare Pages', items, error: 'Missing CLOUDFLARE_API_TOKEN or CLOUDFLARE_ACCOUNT_ID' };

  try {
    const r = await fetch(`https://api.cloudflare.com/client/v4/accounts/${account_id}/pages/projects/tgpc`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (r.ok) {
      const d: any = await r.json();
      items.push({ label: 'Project', used: d.result?.name || 'tgpc', limit: null, pct: '-' });
    }
  } catch {}

  return { name: 'Cloudflare Pages', items };
}

async function checkResend(env: Record<string, string>): Promise<ServiceQuota> {
  const items: ServiceQuota['items'] = [];
  const key = env['RESEND_API_KEY'];
  if (!key) return { name: 'Resend (Email)', items, error: 'Missing RESEND_API_KEY' };

  try {
    await fetch('https://api.resend.com/emails?limit=1', {
      headers: { Authorization: `Bearer ${key}`, 'User-Agent': 'tgpc/2.0' }
    });
    items.push({ label: 'Status', used: 'API reachable', limit: '', pct: '-' });
    items.push({ label: 'Daily Limit', used: '100', limit: '100', pct: '-' });
    items.push({ label: 'Monthly Limit', used: '3,000', limit: '3,000', pct: '-' });
  } catch { items.push({ label: 'API', used: 'Error', limit: '', pct: '-' }); }

  return { name: 'Resend (Email)', items };
}

export async function GET({ request, platform }) {
  const env: Record<string, string> = (platform?.env || {}) as Record<string, string>;

  const quotaSecret = env['QUOTA_SECRET'];
  if (quotaSecret) {
    const header = request.headers.get('x-quota-secret');
    if (header !== quotaSecret) {
      return new Response('Unauthorized', { status: 403 });
    }
  }

  const missing: string[] = [];

  const services = await Promise.all([
    checkSupabase(env),
    checkR2(env),
    checkPages(env),
    checkResend(env),
  ]);

  const report: QuotaReport = {
    generated_at: new Date().toISOString(),
    services,
    missing_vars: missing,
  };

  return json(report, {
    headers: { 'Cache-Control': 'no-cache, max-age=0' }
  });
}
