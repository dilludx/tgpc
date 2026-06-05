<script lang="ts">
  import type { Category, CategoryFilter } from '$lib/types';

  let { active, onSelect } = $props<{
    active: CategoryFilter;
    onSelect: (cat: CategoryFilter) => void;
  }>();

  const categories: CategoryFilter[] = ['all', 'BPharm', 'DPharm', 'MPharm', 'PharmD', 'QC', 'QP'];
</script>

<div class="flex gap-1.5 overflow-x-auto pb-1" style="scrollbar-width:none" role="tablist" aria-label="Filter by category">
  {#each categories as cat}
    <button
      role="tab"
      aria-selected={cat === active}
      onclick={() => onSelect(cat)}
      class="flex-shrink-0 px-4 py-2 rounded-xl text-[0.8rem] font-semibold transition-all cursor-pointer border-none active:scale-95"
      style={cat === active
        ? 'background:#00cc66;color:#fff;box-shadow:0 2px 8px #00cc6640'
        : 'background:white;color:#6b7280;border:1.5px solid #e5e7eb;box-shadow:0 1px 2px rgba(0,0,0,0.02)'}
    >
      {cat === 'all' ? 'All' : cat}
    </button>
  {/each}
</div>
