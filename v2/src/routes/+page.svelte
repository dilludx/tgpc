<script lang="ts">
  import type { PharmacistRecord, CategoryFilter } from '$lib/types';
  import { searchRecords } from '$lib/api';
  import SearchBar from '$lib/components/SearchBar.svelte';
  import FilterChips from '$lib/components/FilterChips.svelte';
  import ResultsTable from '$lib/components/ResultsTable.svelte';
  import MobileCards from '$lib/components/MobileCards.svelte';
  import Pagination from '$lib/components/Pagination.svelte';
  import ExportButtons from '$lib/components/ExportButtons.svelte';
  import Spinner from '$lib/components/Spinner.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';

  let query = $state('');
  let category = $state<CategoryFilter>('all');
  let page = $state(1);
  let loading = $state(false);
  let allResults = $state<PharmacistRecord[]>([]);
  let searching = $state(false);

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

<div class="space-y-4">
  <div class="bg-white border border-tgpc-gray-border rounded-lg p-2.5 sm:p-3">
    <SearchBar bind:query {onSearch} {onReset} {searching} {loading} />

    {#if searching}
      <div class="mt-3">
        <FilterChips active={category} onSelect={setCategory} />
      </div>
    {/if}
  </div>

  {#if searching}
    <div class="bg-white border border-tgpc-gray-border rounded-lg p-2.5 sm:p-3"
         style="max-height:calc(100vh - 275px);overflow-y:auto">
      <div class="flex items-center justify-between mb-2 pb-2 border-b border-tgpc-table-border">
        <span class="text-[0.8rem] text-tgpc-gray-muted">
          {filtered.length} result{filtered.length !== 1 ? 's' : ''}
        </span>
        <ExportButtons records={filtered} keyword={query} />
      </div>

      {#if loading}
        <Spinner label="Searching…" />
      {:else if filtered.length === 0}
        <EmptyState message="No results found" />
      {:else}
        <div class="hidden md:block"><ResultsTable records={paginated} /></div>
        <div class="md:hidden"><MobileCards records={paginated} /></div>

        <Pagination
          {page}
          totalPages={totalPages}
          total={filtered.length}
          perPage={PER_PAGE}
          onPrev={() => page > 1 && page--}
          onNext={() => page < totalPages && page++}
        />
      {/if}
    </div>
  {/if}
</div>
