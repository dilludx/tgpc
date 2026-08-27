import type { PharmacistRecord, Notice, DispatchFile, Stats, Category } from './types';
import { supabase } from './supabase';

// Server-side result cap: keeps payloads and DOM light (CODE_REVIEW.md H5).
export const SEARCH_CAP = 500;

// Strip PostgREST filter syntax (,()) and LIKE wildcards (%_*) so raw input can
// never alter the fallback .or() expression (CODE_REVIEW.md H4).
function sanitizeQuery(s: string): string {
  return s.replace(/[,()%_*]/g, ' ').replace(/\s+/g, ' ').trim();
}

// ilike values are escaped by supabase-js, but % and _ would still act as
// wildcards — strip them so user input matches literally.
function stripWildcards(s: string): string {
  return s.replace(/[%_*]/g, ' ').replace(/\s+/g, ' ').trim();
}

export async function searchRecords(query: string): Promise<PharmacistRecord[]> {
  const q = query.trim();
  if (q.length < 3) return [];
  try {
    const { data, error } = await supabase.rpc('search_pharmacists', { q, lim: SEARCH_CAP });
    if (error) throw error;
    return sortRecords((data as PharmacistRecord[]) || []);
  } catch {
    try {
      const safe = sanitizeQuery(q);
      const { data } = await supabase
        .from('rph')
        .select('registration_number, name, father_name, category, gender, validity_date, status, photo_url')
        .or(`registration_number.ilike.%${safe}%,name.ilike.%${safe}%`)
        .limit(SEARCH_CAP);
      return sortRecords(data || []);
    } catch {
      return [];
    }
  }
}

export interface AdvancedFilters {
  name?: string;
  father_name?: string;
  registration_number?: string;
  category?: Category[];
  gender?: string;
  status?: string;
  valid_till?: string;
}

const VALIDITY_RE = /^(\d{2})-([A-Za-z]{3})-(\d{4})$/;
const MONTHS: Record<string, number> = {
  Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5,
  Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11
};

function parseValidityDate(v: string): Date | null {
  const m = v.trim().match(VALIDITY_RE);
  if (!m) return null;
  const month = MONTHS[m[2]];
  if (month === undefined) return null;
  return new Date(parseInt(m[3], 10), month, parseInt(m[1], 10));
}

export async function advancedSearch(f: AdvancedFilters): Promise<PharmacistRecord[]> {
  try {
    let query = supabase
      .from('rph')
      .select('registration_number, name, father_name, category, gender, validity_date, status, photo_url');
    if (f.name && f.name.trim()) query = query.ilike('name', `%${stripWildcards(f.name)}%`);
    if (f.father_name && f.father_name.trim()) query = query.ilike('father_name', `%${stripWildcards(f.father_name)}%`);
    if (f.registration_number && f.registration_number.trim()) query = query.ilike('registration_number', `${stripWildcards(f.registration_number)}%`);
    if (f.category && f.category.length > 0) query = query.in('category', f.category);
    if (f.gender && f.gender !== 'Any') query = query.eq('gender', f.gender);
    if (f.status && f.status !== 'Any') query = query.eq('status', f.status);
    const { data, error } = await query.limit(SEARCH_CAP);
    if (error) throw error;
    const rows = (data as PharmacistRecord[]) || [];
    if (!f.valid_till) return sortRecords(rows);
    const ref = new Date(f.valid_till + 'T00:00:00');
    const filtered = rows.filter((r) => {
      const d = parseValidityDate(r.validity_date || '');
      if (!d) return false;
      return d.getTime() === ref.getTime();
    });
    return sortRecords(filtered);
  } catch {
    return [];
  }
}

export async function getRecord(regNo: string): Promise<PharmacistRecord | null> {
  const clean = regNo.trim().toUpperCase();
  if (!clean) return null;
  try {
    const { data, error } = await supabase
      .from('rph')
      .select('registration_number, name, father_name, category, gender, validity_date, status, photo_url, serial_number, education, work_experience')
      .eq('registration_number', clean)
      .single();
    if (error || !data) return null;
    return data as PharmacistRecord;
  } catch {
    return null;
  }
}

export async function getStats(): Promise<Stats | null> {
  try {
    const { data, error } = await supabase.rpc('get_rph_stats');
    if (error) throw error;
    if (data && typeof data === 'object') {
      const d = data as { total: number; active: number; inactive: number; categories: Record<string, number> };
      return {
        total: d.total ?? 0,
        active: d.active ?? 0,
        inactive: d.inactive ?? 0,
        BPharm: d.categories?.BPharm ?? 0,
        DPharm: d.categories?.DPharm ?? 0,
        MPharm: d.categories?.MPharm ?? 0,
        PharmD: d.categories?.PharmD ?? 0,
        QC: d.categories?.QC ?? 0,
        QP: d.categories?.QP ?? 0
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
