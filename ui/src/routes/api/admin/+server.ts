import { dev } from '$app/environment';
import {
  SESSION_COOKIE,
  SESSION_TTL_SECONDS,
  createSession,
  getAdminSecret,
  safeEqual
} from '$lib/server/auth';
import type { RequestHandler } from './$types';

/** Log in: verify the shared secret, then issue an HttpOnly session cookie. */
export const POST: RequestHandler = async ({ request, platform, cookies }) => {
  const adminSecret = getAdminSecret(platform);
  if (!adminSecret) {
    return new Response('Not configured', { status: 500 });
  }

  const body = await request.json().catch(() => null);
  const secret = (body as { secret?: unknown } | null)?.secret;

  if (typeof secret !== 'string' || !(await safeEqual(secret, adminSecret))) {
    return new Response('Unauthorized', { status: 403 });
  }

  cookies.set(SESSION_COOKIE, await createSession(adminSecret), {
    path: '/',
    httpOnly: true,
    secure: !dev,
    sameSite: 'strict',
    maxAge: SESSION_TTL_SECONDS
  });

  return new Response(JSON.stringify({ ok: true }), {
    headers: { 'Content-Type': 'application/json' }
  });
};

/** Log out: clear the session cookie. */
export const DELETE: RequestHandler = async ({ cookies }) => {
  cookies.delete(SESSION_COOKIE, { path: '/' });
  return new Response(JSON.stringify({ ok: true }), {
    headers: { 'Content-Type': 'application/json' }
  });
};
