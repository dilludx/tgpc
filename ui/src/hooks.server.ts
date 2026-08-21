import type { Handle } from '@sveltejs/kit';
import { PUBLIC_R2_PHOTO_BASE, PUBLIC_SUPABASE_URL } from '$env/static/public';

// Security headers applied to every function response (CODE_REVIEW.md H6).
// Mirrors `ui/static/_headers`, which covers static assets served directly by
// Cloudflare Pages (those bypass SvelteKit + this hook).
const imgHost = new URL(PUBLIC_R2_PHOTO_BASE).origin;
const connectHost = new URL(PUBLIC_SUPABASE_URL).origin;

const headers: Record<string, string> = {
	'Content-Security-Policy': [
		"default-src 'self'",
		"script-src 'self' 'unsafe-inline'", // SvelteKit hydration data blob
		"style-src 'self' 'unsafe-inline'", // Svelte transitions + style attributes
		`img-src 'self' data: ${imgHost}`,
		`connect-src 'self' ${connectHost}`,
		"font-src 'self'",
		"object-src 'none'",
		"base-uri 'self'",
		"form-action 'self'",
		"frame-ancestors 'none'"
	].join('; '),
	'X-Content-Type-Options': 'nosniff',
	'X-Frame-Options': 'DENY',
	'Referrer-Policy': 'strict-origin-when-cross-origin',
	'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
	'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), interest-cohort=()'
};

export const handle: Handle = async ({ event, resolve }) => {
	const response = await resolve(event);
	for (const [key, value] of Object.entries(headers)) {
		response.headers.set(key, value);
	}
	return response;
};
