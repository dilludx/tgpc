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

  let h = $derived(String(now.getHours()).padStart(2,'0'));
  let m = $derived(String(now.getMinutes()).padStart(2,'0'));
</script>

<div class="min-h-screen flex flex-col bg-white">
  <header class="sticky top-0 z-50 bg-white border-b border-[#e5e7eb]">
    <div class="max-w-5xl mx-auto px-4 sm:px-6 py-2.5 flex items-center justify-between">
      <a href="/" class="no-underline flex items-center gap-1.5">
        <span class="text-[1.1rem] font-bold tracking-tight" style="color:#111">
          <span style="color:#00cc66">TGPC</span><span style="color:#ef4444">Rx</span>
        </span>
      </a>
      <div class="flex items-center gap-3">
        <span class="text-[0.75rem] text-[#6b7280] tabular-nums">
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

  <main class="flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 py-6 pb-20">
    {@render children()}
  </main>

  <footer class="fixed bottom-0 w-full bg-white border-t border-[#e5e7eb]">
    <div class="max-w-5xl mx-auto px-4 sm:px-6 py-2 flex items-center justify-between text-[0.65rem] text-[#9ca3af]">
      <span>{h}:{m} IST</span>
      <div class="flex items-center gap-3">
        <a href="/notice" class="no-underline text-[#6b7280] hover:text-[#111] transition-colors font-medium">Notices</a>
        <a href="/dispatch" class="no-underline text-[#6b7280] hover:text-[#111] transition-colors font-medium">Dispatch</a>
        <span class="text-[#9ca3af]">&copy; {new Date().getFullYear()}</span>
      </div>
    </div>
  </footer>
</div>
