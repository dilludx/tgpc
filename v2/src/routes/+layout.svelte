<script lang="ts">
  import '../app.css';
  import type { ConnectionStatus } from '$lib/types';
  import { getStats } from '$lib/api';

  let { children } = $props();

  let now = $state(new Date());
  let status = $state<ConnectionStatus>('Busy');
  let total = $state<number | null>(null);

  async function loadStats() {
    status = 'Busy';
    const data = await getStats();
    if (data) {
      total = data.total;
      status = 'Live';
    } else {
      status = 'Offline';
    }
  }

  $effect(() => {
    loadStats();
    const id = setInterval(loadStats, 300_000);
    return () => clearInterval(id);
  });

  $effect(() => {
    const id = setInterval(() => now = new Date(), 1000);
    return () => clearInterval(id);
  });

  let statusConfig = $derived.by(() => ({
    Live: { bg: '#dcfce7', text: '#16a34a', dot: '#00cc66' },
    Busy: { bg: '#fff7ed', text: '#9a3412', dot: '#f97316' },
    Offline: { bg: '#fee2e2', text: '#dc2626', dot: '#ef4444' }
  })[status]);

  let m = $derived(String(now.getMinutes()).padStart(2,'0'));
</script>
<div class="min-h-screen flex flex-col bg-white">
  <header class="sticky top-0 z-50 bg-white border-b border-[#e5e7eb]">
    <div class="w-full px-4 sm:px-6 py-2.5 flex items-center justify-between">
      <a href="/" class="no-underline flex items-center gap-1.5">
          <span class="text-[1.1rem] font-bold tracking-tight" style="color:#111">
            <span style="color:#00cc66">TGPC</span><span style="color:#ef4444">Rx</span>
          </span>
        </a>
        <div class="flex items-center gap-3">
          <a href="/notice" class="no-underline text-[#6b7280] hover:text-[#111] transition-colors font-medium text-[0.75rem]">Notices</a>
          <a href="/dispatch" class="no-underline text-[#6b7280] hover:text-[#111] transition-colors font-medium text-[0.75rem]">Dispatch</a>
          <span class="w-px h-3 bg-[#e5e7eb]"></span>
          <span class="text-[0.7rem] text-[#9ca3af] tabular-nums">
            {total ? total.toLocaleString() : '—'} records
          </span>
          <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[0.6rem] font-semibold"
                style="background:{statusConfig.bg};color:{statusConfig.text}">
            <span class="w-1.5 h-1.5 rounded-full" style="background:{statusConfig.dot}"></span>
            {status}
          </span>
        </div>
    </div>
  </header>

  <main class="flex-1 w-full px-4 sm:px-6 py-6 pb-20">
    {@render children()}
  </main>

  <footer class="fixed bottom-0 w-full bg-white border-t border-[#e5e7eb] py-2 text-[0.55rem] text-[#9ca3af] leading-relaxed"
          style="padding-bottom:calc(0.5rem + env(safe-area-inset-bottom, 0px))">
    <div class="w-full px-4 sm:px-6 flex items-center justify-between gap-4">
      <span class="text-left flex-1 pr-4" style="text-wrap:balance">DISCLAIMER: This is an unofficial, third-party tool not affiliated with TGPC or any government body. Data is for reference only — verify all information from official sources before use. Users assume all risk.<br>No warranty as to accuracy, completeness, or timeliness. No liability for errors, omissions, or actions taken based on this content. Operated under fair dealing (Indian Copyright Act, 1957, Section 52).</span>
      <span class="text-right whitespace-nowrap font-semibold flex-shrink-0 text-[0.65rem]">TGPC Rx Registry &copy; 2026</span>
    </div>
  </footer>
</div>
