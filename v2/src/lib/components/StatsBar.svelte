<script lang="ts">
  import type { Stats } from '$lib/types';
  import { fmtNumber } from '$lib/utils';

  let { stats, loading = false }: { stats: Stats; loading?: boolean } = $props();

  const items: { label: string; key: keyof Stats; color: string }[] = [
    { label: 'Total Rx', key: 'total', color: '#00cc66' },
    { label: 'BPharm', key: 'bpharm', color: '#166534' },
    { label: 'DPharm', key: 'dpharm', color: '#854d0e' },
    { label: 'MPharm', key: 'mpharm', color: '#5b21b6' },
    { label: 'PharmD', key: 'pharmd', color: '#991b1b' },
    { label: 'QC', key: 'qc', color: '#1e40af' },
    { label: 'QP', key: 'qp', color: '#9a3412' }
  ];
</script>

<div class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2">
  {#each items as { label, key, color }}
    <div class="bg-white border border-tgpc-gray-border rounded-xl px-3 py-3 text-center shadow-sm card-hover">
      <div class="flex items-center justify-center gap-1.5 mb-1">
        <span class="w-2 h-2 rounded-full inline-block" style="background:{color}"></span>
        <span class="text-[0.6rem] font-semibold text-tgpc-gray-light uppercase tracking-widest">{label}</span>
      </div>
      <div class="text-[1.35rem] font-bold text-tgpc-text tabular-nums tracking-tight">
        {#if loading}
          <span class="text-tgpc-gray-muted">—</span>
        {:else}
          {fmtNumber(stats[key])}
        {/if}
      </div>
    </div>
  {/each}
</div>
