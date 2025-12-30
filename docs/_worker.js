export default {
    async fetch(request, env) {
        const url = new URL(request.url);
        const path = url.pathname;

        // For root path, detect device and serve appropriate HTML
        if (path === '/' || path === '') {
            const ua = request.headers.get('User-Agent') || '';
            const isMobile = /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(ua);

            const targetPath = isMobile ? '/mobile.html' : '/index.html';
            const newUrl = new URL(request.url);
            newUrl.pathname = targetPath;

            return env.ASSETS.fetch(newUrl.toString());
        }

        // For all other paths, serve as normal
        return env.ASSETS.fetch(request);
    }
};
