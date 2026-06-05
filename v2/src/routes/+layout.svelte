<script lang="ts">
  import '../app.css';
  import type { Stats, ConnectionStatus } from '$lib/types';
  import { getStats } from '$lib/api';
  import StatusPill from '$lib/components/StatusPill.svelte';
  import StatsBar from '$lib/components/StatsBar.svelte';
  import SyncRow from '$lib/components/SyncRow.svelte';
  import Skeleton from '$lib/components/Skeleton.svelte';

  let { children } = $props();

  let now = $state(new Date());
  let status = $state<ConnectionStatus>('Busy');
  let stats = $state<Stats>({ total: 0, bpharm: 0, dpharm: 0, mpharm: 0, pharmd: 0, qc: 0, qp: 0 });
  let statsLoading = $state(true);

  async function loadStats() {
    status = 'Busy';
    statsLoading = true;
    const data = await getStats();
    if (data) {
      stats = data;
      status = 'Live';
    } else {
      status = 'Offline';
    }
    statsLoading = false;
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

<div class="min-h-screen flex flex-col bg-[#f0f2f5]">
  <!-- Header -->
  <header class="sticky top-0 z-50 bg-white/90 backdrop-blur-lg border-b border-tgpc-gray-border shadow-sm">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <div class="flex items-center gap-3">
          <a href="/" class="no-underline flex items-center gap-2" aria-label="Home">
            <div class="w-9 h-9 rounded-xl bg-[#00cc66] flex items-center justify-center shadow-sm">
              <span class="text-white font-bold text-sm">T</span>
            </div>
            <div>
              <span class="text-[1.2rem] font-bold tracking-tight" style="line-height:1.2">
                <span style="color:#00cc66">TGPC</span><span style="color:#ef4444">Rx</span>
              </span>
              <div class="text-[0.6rem] text-tgpc-gray-muted font-medium uppercase tracking-widest" style="margin-top:-1px">Registry</div>
            </div>
          </a>
          <StatusPill {status} />
        </div>
      </div>

      <div class="mt-4">
        <StatsBar {stats} loading={statsLoading} />
      </div>

      <div class="mt-3"><SyncRow {now} /></div>
    </div>
  </header>

  <!-- Main -->
  <main class="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 pb-24">
    {@render children()}
  </main>

  <!-- Footer -->
  <footer class="fixed bottom-0 w-full bg-white/90 backdrop-blur-sm border-t border-tgpc-gray-border px-4 py-3 text-center text-[0.6rem] text-tgpc-gray-muted leading-relaxed"
          style="padding-bottom:calc(0.75rem + env(safe-area-inset-bottom, 0px))">
    <span class="inline-flex items-center gap-1.5">
      <span class="w-1 h-1 rounded-full bg-tgpc-gray-muted inline-block"></span>
      DISCLAIMER: This is an unofficial tool for reference only. No liability for errors or omissions.
      <span class="w-1 h-1 rounded-full bg-tgpc-gray-muted inline-block"></span>
      Fair Dealing, Section 52, Indian Copyright Act 1957
      <span class="w-1 h-1 rounded-full bg-tgpc-gray-muted inline-block"></span>
      &copy; {new Date().getFullYear()} TGPC Rx Registry
    </span>
  </footer>
</div>
