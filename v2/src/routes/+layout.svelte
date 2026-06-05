<script lang="ts">
  import '../app.css';
  import type { Stats, ConnectionStatus } from '$lib/types';
  import { getStats } from '$lib/api';
  import StatusPill from '$lib/components/StatusPill.svelte';
  import StatsBar from '$lib/components/StatsBar.svelte';
  import SyncRow from '$lib/components/SyncRow.svelte';

  let { children } = $props();

  let now = $state(new Date());
  let status = $state<ConnectionStatus>('Offline');
  let stats = $state<Stats>({ total: 0, bpharm: 0, dpharm: 0, mpharm: 0, pharmd: 0, qc: 0, qp: 0 });

  async function loadStats() {
    status = 'Busy';
    const data = await getStats();
    if (data) {
      stats = data;
      status = 'Live';
    } else {
      status = 'Offline';
    }
  }

  $effect(() => {
    loadStats();
    const poll = setInterval(loadStats, 300_000);
    return () => clearInterval(poll);
  });

  $effect(() => {
    const id = setInterval(() => now = new Date(), 1000);
    return () => clearInterval(id);
  });
</script>

<div class="min-h-screen flex flex-col bg-tgpc-bg">
  <nav class="sticky top-0 z-50 bg-white shadow-sm">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
      <div class="flex items-center justify-between flex-wrap gap-y-2">
        <div class="flex items-center gap-1.5">
          <span class="text-[1.25rem] max-md:text-[1.1rem] max-sm:text-[1rem] font-bold">
            <span style="color:#00cc66">TGPC</span>
            <span style="color:#ef4444">Rx</span>
            <span style="color:#808080">Registry</span>
          </span>
          <span class="ml-3"><StatusPill {status} /></span>
        </div>
      </div>

      <div class="mt-3"><StatsBar {stats} /></div>

      <div class="mt-2"><SyncRow {now} /></div>
    </div>
  </nav>

  <main class="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 pb-20">
    {@render children()}
  </main>

  <footer class="fixed bottom-0 w-full bg-white border-t border-tgpc-gray-border py-2 px-4 text-center text-[0.55rem] text-tgpc-gray-muted leading-relaxed"
          style="padding-bottom:calc(0.5rem + env(safe-area-inset-bottom, 0px))">
    &#9888; DISCLAIMER: This is an unofficial tool. Data is for reference only. &#128683; No liability for errors or omissions.
    &#9878; Indian Copyright Act, 1957 — Section 52 (Fair Dealing). &copy; {new Date().getFullYear()}
  </footer>
</div>
