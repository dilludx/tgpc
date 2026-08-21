/**
 * Tiny localStorage value cache (used by the stats/notice/dispatch pages).
 * Guarded for SSR and thrown errors so a stale/corrupt entry never breaks a
 * first load. Shared to remove the copy-pasted variants that lived in each
 * component (CODE_REVIEW.md L2).
 */

export function cachedOrNull<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const { data, expiry } = JSON.parse(raw);
    if (Date.now() > expiry) {
      localStorage.removeItem(key);
      return null;
    }
    return data as T;
  } catch {
    return null;
  }
}

export function setCache<T>(key: string, data: T, ttl = 300_000) {
  try {
    localStorage.setItem(key, JSON.stringify({ data, expiry: Date.now() + ttl }));
  } catch {}
}
