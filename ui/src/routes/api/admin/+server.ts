export async function POST({ request, platform }) {
  const env: Record<string, string> = (platform?.env || {}) as Record<string, string>;

  const adminSecret = env['ADMIN_SECRET'] || env['QUOTA_SECRET'];
  if (!adminSecret) {
    return new Response('Not configured', { status: 500 });
  }

  const body = await request.json().catch(() => null);
  const secret = body?.secret;
  if (typeof secret !== 'string' || secret !== adminSecret) {
    return new Response('Unauthorized', { status: 403 });
  }

  return new Response(JSON.stringify({ ok: true }), {
    headers: { 'Content-Type': 'application/json' }
  });
}