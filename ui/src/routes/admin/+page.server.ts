import type { PageServerLoad } from './$types';
import type { QuotaReport } from '$lib/types';
import { env as privateEnv } from '$env/dynamic/private';

export const load: PageServerLoad = async ({ fetch }) => {
  let report: QuotaReport | null = null;
  try {
    const secret = privateEnv['QUOTA_SECRET'];
    const r = await fetch('/api/quota', {
      headers: secret ? { 'x-quota-secret': secret } : {}
    });
    if (r.ok) report = await r.json();
  } catch {}
  return { report };
};