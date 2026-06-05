<script lang="ts">
  import type { Category, CategoryFilter } from '$lib/types';

  let { active, onSelect } = $props<{
    active: CategoryFilter;
    onSelect: (cat: CategoryFilter) => void;
  }>();

  const categories: CategoryFilter[] = ['all', 'BPharm', 'DPharm', 'MPharm', 'PharmD', 'QC', 'QP'];
</script>

<div class="flex gap-2 overflow-x-auto pb-1" style="scrollbar-width:none;-ms-overflow-style:none" role="tablist" aria-label="Filter by category">
  {#each categories as cat}
    <button
      role="tab"
      aria-selected={cat === active}
      onclick={() => onSelect(cat)}
      class="flex-shrink-0 px-3 py-1.5 rounded-full text-[0.75rem] font-medium transition-colors cursor-pointer border-none"
      style={cat === active
        ? 'background:#00cc66;color:#fff'
        : 'background:transparent;color:#6b7280;border:1px solid #e5e7eb'}
    >
      {cat === 'all' ? 'All' : cat}
    </button>
  {/each}
</div>
