// Best-effort, in-isolate brute-force limiter for login endpoints
// (CODE_REVIEW.md H7). Each Pages isolate holds its own window, so this is
// defence-in-depth rather than a substitute for a Cloudflare Rate Limiting
// rule on /api/admin — set that in the dashboard too.
const WINDOW_MS = 60_000;
const MAX_ATTEMPTS = 5;

const attempts = new Map<string, number[]>();

export function rateLimited(key: string): boolean {
	const now = Date.now();
	const recent = (attempts.get(key) ?? []).filter((t) => now - t < WINDOW_MS);
	if (recent.length >= MAX_ATTEMPTS) {
		attempts.set(key, recent);
		return true;
	}
	recent.push(now);
	attempts.set(key, recent);
	return false;
}
