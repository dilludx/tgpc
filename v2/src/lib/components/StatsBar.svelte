<script lang="ts">
  import type { Stats } from '$lib/types';

  let { stats }: { stats: Stats } = $props();

  const items: { label: string; key: keyof Stats }[] = [
    { label: 'Total Rx', key: 'total' },
    { label: 'BPharm', key: 'bpharm' },
    { label: 'DPharm', key: 'dpharm' },
    { label: 'MPharm', key: 'mpharm' },
    { label: 'PharmD', key: 'pharmd' },
    { label: 'QC', key: 'qc' },
    { label: 'QP', key: 'qp' }
  ];

  function fmt(n: number): string {
    return n?.toLocaleString() || '—';
  }
</script>

<div class="grid grid-cols-4 md:flex md:flex-row border border-tgpc-gray-border rounded-lg overflow-hidden max-sm:grid-cols-2">
  {#each items as { label, key }}
    <div class="flex-1 px-3 py-2 text-center md:border-r border-tgpc-gray-border last:border-r-0 max-sm:[&:nth-child(6)]:hidden max-sm:[&:nth-child(7)]:hidden">
      <div class="text-[0.7rem] font-semibold text-tgpc-gray-light uppercase tracking-wide">{label}</div>
      <div class="text-[1.25rem] max-md:text-[0.95rem] font-bold text-tgpc-text">{fmt(stats[key])}</div>
    </div>
  {/each}
</div>
