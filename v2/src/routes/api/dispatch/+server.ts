import { json } from '@sveltejs/kit';

const FALLBACK_DATA = [
  'DL27042026.pdf', 'DL23022026.pdf', 'DL20042026.pdf', 'DL16022026.pdf',
  'DL10032026.pdf', 'DL09022026.pdf', 'DL04052026.pdf', 'DL04042026.pdf',
  'DL27022026.pdf', 'DL07012026.pdf', 'DL22012026.pdf', 'DL30012026.pdf',
  'DL01062026.pdf', 'DL27052026.pdf', 'DL18052026.pdf',
  'DL03062020C.pdf', 'DL03062020D.pdf', 'DL11102021AD.pdf',
  'DL01112023.pdf', 'DL02042024.pdf', 'DL03062025.pdf', 'DL04052024.pdf',
  'DL05102019.pdf', 'DL07092019.pdf', 'DL10052019.pdf', 'DL16022019.pdf',
  'DL18042019.pdf', 'DL21022018.pdf', 'DL30032019.pdf', 'DL31012025.pdf'
];

const LIVE_API = 'https://tgpc.pages.dev/api/dispatch';

export async function GET({ platform, fetch }) {
  try {
    const bucket: any = platform?.env?.DISPATCH;
    if (bucket && typeof bucket.list === 'function') {
      const listing = await bucket.list({ prefix: 'dispatch/' });
      const files = listing.objects.map((obj: any) => ({
        name: obj.key.replace('dispatch/', ''),
        size: obj.size
      }));
      if (files.length > 0) return json(files, { headers: { 'Cache-Control': 'public, max-age=300' } });
    }
  } catch {}

  try {
    const resp = await fetch(LIVE_API);
    if (resp.ok) return json(await resp.json());
  } catch {}

  const fallback = FALLBACK_DATA.map(n => ({
    name: n,
    size: Math.round(50000 + Math.random() * 200000)
  }));
  return json(fallback, { headers: { 'Cache-Control': 'public, max-age=300' } });
}
