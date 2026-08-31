import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ params, platform }) => {
  const name = params.name;
  if (!/^DL\d{2}\d{2}\d{4}[A-Z]*\.pdf$/i.test(name)) {
    return new Response('Not found', { status: 404 });
  }
  try {
    const bucket: any = platform?.env?.DISPATCH;
    if (bucket && typeof bucket.get === 'function') {
      const obj = await bucket.get(`dispatch/${name}`);
      if (obj) {
        const headers = new Headers();
        headers.set('Content-Type', 'application/pdf');
        headers.set('Content-Disposition', `inline; filename="${name}"`);
        headers.set('Cache-Control', 'public, max-age=300');
        if (obj.size) headers.set('Content-Length', String(obj.size));
        return new Response(obj.body, { headers });
      }
    }
  } catch {}
  return new Response('Not found', { status: 404 });
};
