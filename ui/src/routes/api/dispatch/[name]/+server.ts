import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ params, platform }) => {
  const name = params.name;
  // Strict validation: only allow DL files, no path separators, max 30 chars
  if (!/^DL\d{2}\d{2}\d{4}[A-Z]*\.pdf$/i.test(name) || name.includes('/') || name.length > 30) {
    return new Response('Not found', { status: 404 });
  }
  try {
    const bucket: any = platform?.env?.DISPATCH;
    if (bucket && typeof bucket.get === 'function') {
      // R2 key must not contain ../ or start with /
      const r2Key = `dispatch/${name}`;
      if (r2Key.includes('..') || r2Key.startsWith('/')) {
        return new Response('Not found', { status: 404 });
      }
      const obj = await bucket.get(r2Key);
      if (obj) {
        const buf = await obj.arrayBuffer();
        let bytes = new Uint8Array(buf);
        // Rewrite PDF Title metadata so tab shows filename, not 858a…xlsx hash
        try {
          const text = new TextDecoder('latin1').decode(bytes);
          let mod = text.replace(/\/Title\s*\([^)]*\)/g, `/Title (${name})`);
          // Replace XMP dc:title rdf:li value
          mod = mod.replace(/<dc:title>[\s\S]*?<\/dc:title>/g, `<dc:title><rdf:Alt><rdf:li xml:lang="x-default">${name}</rdf:li></rdf:Alt></dc:title>`);
          if (mod !== text) {
            bytes = Uint8Array.from(mod, (ch) => ch.charCodeAt(0) & 0xff);
          }
        } catch {}
        const headers = new Headers();
        headers.set('Content-Type', 'application/pdf');
        headers.set('Content-Disposition', `inline; filename="${name}"; filename*=UTF-8''${encodeURIComponent(name)}`);
        headers.set('Cache-Control', 'public, max-age=60');
        headers.set('Pragma', 'no-cache');
        headers.set('Content-Length', String(bytes.byteLength));
        return new Response(bytes, { headers });
      }
    }
  } catch {}
  return new Response('Not found', { status: 404 });
};
