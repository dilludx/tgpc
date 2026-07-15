import type { PageLoad } from './$types';
import type { QuotaReport } from '$lib/types';

export const load: PageLoad = async ({ fetch }) => {
  let report: QuotaReport | null = null;
  try {
    const r = await fetch('/api/quota');
    if (r.ok) report = await r.json();
  } catch {}
  return { report };
};
