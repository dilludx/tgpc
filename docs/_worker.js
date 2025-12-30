export default {
    async fetch(request, env) {
        const url = new URL(request.url);

        // Skip for static assets
        if (url.pathname.match(/\.(js|css|png|jpg|svg|ico|woff|woff2|html)$/) && url.pathname !== '/index.html') {
            return env.ASSETS.fetch(request);
        }

        // Handle root or index.html
        if (url.pathname === '/' || url.pathname === '/index.html') {
            const ua = request.headers.get('User-Agent') || '';
            const isMobile = /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(ua);

            // Serve appropriate HTML
            const newUrl = new URL(request.url);
            newUrl.pathname = isMobile ? '/mobile.html' : '/index.html';
            return env.ASSETS.fetch(new Request(newUrl, request));
        }

        return env.ASSETS.fetch(request);
    }
};
