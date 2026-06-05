<script lang="ts">
  import '../app.css';
  import { supabase } from '$lib/supabase';
  import { fmtNumber, fmtDate, fmtTime } from '$lib/utils';

  let { children } = $props();

  type Status = 'Live' | 'Busy' | 'Offline';
  type StatEntry = { label: string; value: number };

  let now = $state(new Date());
  let status = $state<Status>('Offline');
  let stats = $state<StatEntry[]>([
    { label: 'Total Rx', value: 0 },
    { label: 'BPharm', value: 0 },
    { label: 'DPharm', value: 0 },
    { label: 'MPharm', value: 0 },
    { label: 'PharmD', value: 0 },
    { label: 'QC', value: 0 },
    { label: 'QP', value: 0 }
  ]);

  const STATUS_DOT: Record<Status, string> = {
    Live: 'bg-tgpc-green',
    Busy: 'bg-gray-400',
    Offline: 'bg-red-500'
  };

  async function loadStats() {
    status = 'Busy';
    try {
      const { data, error } = await supabase.rpc('get_rx_counts');
      if (error) throw error;
      if (data && typeof data === 'object') {
        const d = data as Record<string, number>;
        stats = [
          { label: 'Total Rx', value: (d.bpharm ?? 0) + (d.dpharm ?? 0) + (d.mpharm ?? 0) + (d.pharmd ?? 0) + (d.qc ?? 0) + (d.qp ?? 0) },
          { label: 'BPharm', value: d.bpharm ?? 0 },
          { label: 'DPharm', value: d.dpharm ?? 0 },
          { label: 'MPharm', value: d.mpharm ?? 0 },
          { label: 'PharmD', value: d.pharmd ?? 0 },
          { label: 'QC', value: d.qc ?? 0 },
          { label: 'QP', value: d.qp ?? 0 }
        ];
      }
      status = 'Live';
    } catch {
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
  <!-- Sticky Header -->
  <nav class="sticky top-0 z-50 bg-white shadow-sm">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
      <div class="flex items-center justify-between flex-wrap gap-y-2">
        <!-- Brand -->
        <div class="flex items-center gap-1.5">
          <span class="text-[1.25rem] max-md:text-[1.1rem] max-sm:text-[1rem] font-bold">
            <span style="color:#00cc66">TGPC</span>
            <span style="color:#ef4444">Rx</span>
            <span style="color:#808080">Registry</span>
          </span>
          <span class="ml-3 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[0.625rem] max-md:text-[0.7rem] font-medium"
             style="background:{status === 'Live' ? '#dcfce7' : status === 'Offline' ? '#fee2e2' : '#f3f4f6'};color:{status === 'Live' ? '#16a34a' : status === 'Offline' ? '#dc2626' : '#6b7280'}">
            <span class="inline-block w-1.5 h-1.5 rounded-full {STATUS_DOT[status]}"></span>
            {status}
          </span>
        </div>
      </div>

      <!-- Stats Bar -->
      <div class="mt-3 grid grid-cols-4 md:flex md:flex-row border border-tgpc-gray-border rounded-lg overflow-hidden max-sm:grid-cols-2">
        {#each stats as stat}
          <div class="flex-1 px-3 py-2 text-center md:border-r border-tgpc-gray-border last:border-r-0 max-sm:[&:nth-child(6)]:hidden max-sm:[&:nth-child(7)]:hidden">
            <div class="text-[0.7rem] font-semibold text-tgpc-gray-light uppercase tracking-wide">{stat.label}</div>
            <div class="text-[1.25rem] max-md:text-[0.95rem] font-bold text-tgpc-text">{fmtNumber(stat.value)}</div>
          </div>
        {/each}
      </div>

      <!-- Sync Row -->
      <div class="mt-2 flex items-center gap-2 text-[0.75rem] text-tgpc-gray-muted flex-wrap">
        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-[10px] text-[0.7rem] font-semibold"
              style="background:linear-gradient(135deg,#00cc66,#00cc6640);color:#fff">
          ✓ Synced
        </span>
        <span style="background:linear-gradient(135deg,#7c3aed,#2563eb);-webkit-background-clip:text;-webkit-text-fill-color:transparent">
          { fmtDate(now) } { fmtTime(now) }
        </span>
        <span>|</span>
        <a href="/notice" class="text-tgpc-purple no-underline hover:underline font-medium">NOTICES</a>
        <a href="/dispatch" class="text-tgpc-red no-underline hover:underline font-medium"
           style="animation:pulse-border 2s ease-in-out infinite">DISPATCH</a>
        <span>|</span>
        <span class="text-tgpc-gray-muted">Unofficial data | Not for legal use</span>
      </div>
    </div>
  </nav>

  <!-- Main Content -->
  <main class="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 pb-20">
    {@render children()}
  </main>

  <!-- Fixed Footer -->
  <footer class="fixed bottom-0 w-full bg-white border-t border-tgpc-gray-border py-2 px-4 text-center text-[0.55rem] text-tgpc-gray-muted leading-relaxed"
          style="padding-bottom:calc(0.5rem + env(safe-area-inset-bottom, 0px))">
    ⚠️ DISCLAIMER: This is an unofficial tool. Data is for reference only. 🚫 No liability for errors or omissions.
    ⚖️ Indian Copyright Act, 1957 — Section 52 (Fair Dealing). &copy; {new Date().getFullYear()}
  </footer>
</div>
