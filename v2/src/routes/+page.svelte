<script lang="ts">
  import type { PharmacistRecord, CategoryFilter } from '$lib/types';
  import { searchRecords } from '$lib/api';
  import SearchBar from '$lib/components/SearchBar.svelte';
  import FilterChips from '$lib/components/FilterChips.svelte';
  import ResultsTable from '$lib/components/ResultsTable.svelte';
  import MobileCards from '$lib/components/MobileCards.svelte';
  import Pagination from '$lib/components/Pagination.svelte';
  import ExportButtons from '$lib/components/ExportButtons.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import Skeleton from '$lib/components/Skeleton.svelte';

  let query = $state('');
  let category = $state<CategoryFilter>('all');
  let page = $state(1);
  let loading = $state(false);
  let allResults = $state<PharmacistRecord[]>([]);
  let searching = $state(false);
  let searchKey = $state(0);

  const PER_PAGE = 50;

  let filtered = $derived(
    category === 'all'
      ? allResults
      : allResults.filter(r => r.category === category)
  );

  let totalPages = $derived(Math.max(1, Math.ceil(filtered.length / PER_PAGE)));
  let paginated = $derived(filtered.slice((page - 1) * PER_PAGE, page * PER_PAGE));

  async function doSearch() {
    const q = query.trim();
    if (q.length < 3) return;
    loading = true;
    searching = true;
    page = 1;
    allResults = await searchRecords(query);
    searchKey++;
    loading = false;
  }

  function setCategory(cat: CategoryFilter) {
    category = cat;
    page = 1;
  }

  function resetSearch() {
    query = '';
    category = 'all';
    page = 1;
    allResults = [];
    searching = false;
  }
</script>

<div class="space-y-5">
  <!-- Search Section -->
  <div class="bg-white border border-tgpc-gray-border rounded-2xl p-5 shadow-sm card-hover">
    <SearchBar bind:query {onSearch} {onReset} {searching} {loading} />

    {#if searching}
      <div class="mt-4 pt-4 border-t border-tgpc-gray-border">
        <FilterChips active={category} onSelect={setCategory} />
      </div>
    {/if}
  </div>

  <!-- Results -->
  {#if searching}
    <div class="bg-white border border-tgpc-gray-border rounded-2xl p-5 shadow-sm"
         style="max-height:calc(100vh - 275px);overflow-y:auto">
      <div class="flex items-center justify-between mb-4 pb-4 border-b border-tgpc-gray-border">
        <span class="text-[0.85rem] font-semibold text-tgpc-gray-muted tabular-nums">
          {filtered.length} result{filtered.length !== 1 ? 's' : ''}
        </span>
        <ExportButtons records={filtered} keyword={query} />
      </div>

      {#if loading}
        <div class="space-y-3">
          <Skeleton height="3rem" width="100%" />
          <Skeleton height="1.2rem" width="60%" />
          <Skeleton height="1.2rem" width="80%" />
          <Skeleton height="1.2rem" width="45%" />
          <Skeleton height="1.2rem" width="70%" />
          <Skeleton height="1.2rem" width="55%" />
        </div>
      {:else if filtered.length === 0}
        <EmptyState message="No results found" />
      {:else}
        <div class="hidden md:block">
          <ResultsTable records={paginated} />
        </div>
        <div class="md:hidden">
          <MobileCards records={paginated} />
        </div>

        <Pagination
          {page}
          totalPages={totalPages}
          total={filtered.length}
          perPage={PER_PAGE}
          onPrev={() => { if (page > 1) page--; }}
          onNext={() => { if (page < totalPages) page++; }}
        />
      {/if}
    </div>
  {/if}
</div>
