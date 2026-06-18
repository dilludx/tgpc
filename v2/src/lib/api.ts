import type { PharmacistRecord, Notice, DispatchFile, Stats } from './types';
import { supabase } from './supabase';

export async function searchRecords(query: string): Promise<PharmacistRecord[]> {
  if (query.trim().length < 3) return [];
  try {
    const { data } = await supabase
      .from('rph')
      .select('registration_number, name, father_name, category')
      .or(`registration_number.ilike.%${query}%,name.ilike.%${query}%`)
      .limit(100000);
    return sortRecords(data || []);
  } catch {
    return [];
  }
}

export async function getStats(): Promise<Stats | null> {
  try {
    const { data, error } = await supabase.rpc('get_rph_stats');
    if (error) throw error;
    if (data && typeof data === 'object') {
      const d = data as { total: number; categories: Record<string, number> };
      return {
        total: d.total ?? 0,
        bpharm: d.categories?.BPharm ?? d.categories?.bpharm ?? 0,
        dpharm: d.categories?.DPharm ?? d.categories?.dpharm ?? 0,
        mpharm: d.categories?.MPharm ?? d.categories?.mpharm ?? 0,
        pharmd: d.categories?.PharmD ?? d.categories?.pharmd ?? 0,
        qc: d.categories?.QC ?? d.categories?.qc ?? 0,
        qp: d.categories?.QP ?? d.categories?.qp ?? 0
      };
    }
    return null;
  } catch {
    return null;
  }
}

export async function fetchNotices(): Promise<Notice[]> {
  try {
    const resp = await fetch('/api/notice');
    if (!resp.ok) throw new Error('Failed to load notices');
    const data = await resp.json();
    data.sort((a: Notice, b: Notice) => b.date.localeCompare(a.date));
    return data;
  } catch {
    return [];
  }
}

export async function fetchDispatchFiles(): Promise<DispatchFile[]> {
  try {
    const resp = await fetch('/api/dispatch');
    if (!resp.ok) throw new Error('API unavailable');
    return await resp.json();
  } catch {
    return [];
  }
}

function parseReg(reg: string): { prefix: string; num: number } {
  const m = reg.match(/^([A-Z]+)(\d+)$/);
  return m ? { prefix: m[1], num: parseInt(m[2], 10) } : { prefix: reg, num: 0 };
}

function sortRecords(data: PharmacistRecord[]): PharmacistRecord[] {
  return [...data].sort((a, b) => {
    const ra = parseReg(a.registration_number);
    const rb = parseReg(b.registration_number);
    if (ra.prefix !== rb.prefix) return ra.prefix.localeCompare(rb.prefix);
    return ra.num - rb.num;
  });
}
