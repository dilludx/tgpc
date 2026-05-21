const SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
};

function addSecurityHeaders(response) {
    const headers = new Headers(response.headers);
    for (const [key, value] of Object.entries(SECURITY_HEADERS)) {
        if (!headers.has(key)) {
            headers.set(key, value);
        }
    }
    return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers,
    });
}

export default {
    async fetch(request, env) {
        const url = new URL(request.url);
        const path = url.pathname;

        // API: list dispatch files from R2
        if (path === '/api/dispatch-files') {
            try {
                const listing = await env.DISPATCH_BUCKET.list({ prefix: 'dispatchlist/' });
                const files = listing.objects.map(obj => ({
                    name: obj.key.replace('dispatchlist/', ''),
                    size: obj.size
                }));
                return addSecurityHeaders(new Response(JSON.stringify(files), {
                    headers: { 'Content-Type': 'application/json' }
                }));
            } catch (err) {
                return addSecurityHeaders(new Response(JSON.stringify({ error: err.message }), { status: 500 }));
            }
        }

        // Handle dispatchlist route
        if (path === '/dispatchlist' || path === '/dispatchlist/') {
            const newUrl = new URL(request.url);
            newUrl.pathname = '/dispatchlist.html';
            const response = await env.ASSETS.fetch(newUrl.toString());
            return addSecurityHeaders(response);
        }

        // For root path, detect device and serve appropriate HTML
        if (path === '/' || path === '') {
            const ua = request.headers.get('User-Agent') || '';
            const isMobile = /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(ua);

            const targetPath = isMobile ? '/mobile.html' : '/index.html';
            const newUrl = new URL(request.url);
            newUrl.pathname = targetPath;

            const response = await env.ASSETS.fetch(newUrl.toString());
            return addSecurityHeaders(response);
        }

        // For all other paths, serve as normal
        const response = await env.ASSETS.fetch(request);
        return addSecurityHeaders(response);
    }
};
