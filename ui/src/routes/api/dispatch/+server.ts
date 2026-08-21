import { json } from '@sveltejs/kit';

const FALLBACK_FILES = [
  'DL27042026.pdf', 'DL23022026.pdf', 'DL20042026.pdf', 'DL16022026.pdf',
  'DL10032026.pdf', 'DL09022026.pdf', 'DL04052026.pdf', 'DL04042026.pdf',
  'DL27022026.pdf', 'DL07012026.pdf', 'DL22012026.pdf', 'DL30012026.pdf',
  'DL01062026.pdf', 'DL27052026.pdf', 'DL18052026.pdf',
  'DL03062020C.pdf', 'DL03062020D.pdf', 'DL11102021AD.pdf',
  'DL01112023.pdf', 'DL02042024.pdf', 'DL03062025.pdf', 'DL04052024.pdf',
  'DL05102019.pdf', 'DL07092019.pdf', 'DL10052019.pdf', 'DL16022019.pdf',
  'DL18042019.pdf', 'DL21022018.pdf', 'DL30032019.pdf', 'DL31012025.pdf'
];

export async function GET({ platform }) {
  try {
    const bucket: any = platform?.env?.DISPATCH;
    if (bucket && typeof bucket.list === 'function') {
      const listing = await bucket.list({ prefix: 'dispatch/' });
      const files = listing.objects.map((obj: any) => ({
        name: obj.key.replace('dispatch/', ''),
        size: obj.size
      }));
      if (files.length > 0) {
        return json(files, { headers: { 'Cache-Control': 'public, max-age=300' } });
      }
    }
  } catch {}

  // R2 binding unavailable: return the last-known file list instead of 503
  // so the dispatch page stays usable, but flag every entry stale and omit
  // fabricated sizes (CODE_REVIEW.md M3).
  const files = FALLBACK_FILES.map((n) => ({ name: n, stale: true }));
  return json(files, { headers: { 'Cache-Control': 'public, max-age=300' } });
}
