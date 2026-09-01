import type { Handle } from '@sveltejs/kit';
import { PUBLIC_R2_PHOTO_BASE, PUBLIC_SUPABASE_URL } from '$env/static/public';

// Security headers applied to every function response (CODE_REVIEW.md H6).
// Mirrors `ui/static/_headers`, which covers static assets served directly by
// Cloudflare Pages (those bypass SvelteKit + this hook).
const imgHost = new URL(PUBLIC_R2_PHOTO_BASE).origin;
const connectHost = new URL(PUBLIC_SUPABASE_URL).origin;

// Generate a per-request nonce for inline scripts (CSP hardening).
// SvelteKit injects hydration data as an inline <script>, so 'unsafe-inline'
// is required. A nonce restricts it to scripts we generate, blocking XSS.
function generateNonce(): string {
	const bytes = new Uint8Array(16);
	crypto.getRandomValues(bytes);
	return btoa(String.fromCharCode(...bytes));
}

export const handle: Handle = async ({ event, resolve }) => {
	const nonce = generateNonce();
	const response = await resolve(event, { transformPageChunk: ({ html }) => html.replace('nonce=""', `nonce="${nonce}"`) });

	// Static headers that apply to all responses
	const staticHeaders: Record<string, string> = {
		'X-Content-Type-Options': 'nosniff',
		'X-Frame-Options': 'DENY',
		'Referrer-Policy': 'strict-origin-when-cross-origin',
		'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
		'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), interest-cohort=()',
		// Isolate this origin from cross-origin windows (BFCache + Spectre hardening)
		'Cross-Origin-Opener-Policy': 'same-origin',
		// Prevent other origins from embedding our resources
		'Cross-Origin-Resource-Policy': 'same-origin'
	};

	for (const [key, value] of Object.entries(staticHeaders)) {
		response.headers.set(key, value);
	}

	// CSP with nonce (replaces unsafe-inline for scripts)
	response.headers.set('Content-Security-Policy', [
		"default-src 'self'",
		`script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
		"style-src 'self' 'unsafe-inline'", // Svelte transitions + style attributes
		`img-src 'self' data: ${imgHost}`,
		`connect-src 'self' ${connectHost}`,
		"font-src 'self'",
		"object-src 'none'",
		"base-uri 'self'",
		"form-action 'self'",
		"frame-ancestors 'none'"
	].join('; '));

	return response;
};
