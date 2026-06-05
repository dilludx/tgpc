<script lang="ts">
  import type { Stats } from '$lib/types';
  import { fmtNumber } from '$lib/utils';

  let { stats, loading = false }: { stats: Stats; loading?: boolean } = $props();

  const items: { label: string; key: keyof Stats }[] = [
    { label: 'Total Rx', key: 'total' },
    { label: 'BPharm', key: 'bpharm' },
    { label: 'DPharm', key: 'dpharm' },
    { label: 'MPharm', key: 'mpharm' },
    { label: 'PharmD', key: 'pharmd' },
    { label: 'QC', key: 'qc' },
    { label: 'QP', key: 'qp' }
  ];
</script>

<div class="grid grid-cols-4 md:flex md:flex-row bg-white border border-tgpc-gray-border rounded-xl overflow-hidden shadow-sm max-sm:grid-cols-2">
  {#each items as { label, key }}
    <div class="flex-1 px-3 py-2.5 text-center md:border-r border-tgpc-gray-border last:border-r-0 max-sm:[&:nth-child(6)]:hidden max-sm:[&:nth-child(7)]:hidden">
      <div class="text-[0.65rem] font-semibold text-tgpc-gray-light uppercase tracking-widest">{label}</div>
      <div class="text-[1.3rem] max-md:text-[0.95rem] font-bold text-tgpc-text tabular-nums">
        {loading ? '—' : fmtNumber(stats[key])}
      </div>
    </div>
  {/each}
</div>
