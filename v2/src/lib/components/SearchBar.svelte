<script lang="ts">
  let { query, onSearch, onReset, searching, loading } = $props<{
    query: string;
    onSearch: () => void;
    onReset: () => void;
    searching: boolean;
    loading: boolean;
  }>();
</script>

<div class="space-y-2">
  <h2 class="text-[1.1rem] max-md:text-[0.9rem] font-semibold">
    <span class="text-tgpc-gray-light">Search</span>
    <span style="color:#ef4444">Rx</span>
  </h2>

  <div class="flex flex-col sm:flex-row gap-2">
    <input
      type="text"
      bind:value={query}
      onkeydown={(e) => e.key === 'Enter' && onSearch()}
      placeholder="Enter Name or Registration Number (min 3 chars)"
      aria-label="Search query"
      class="flex-1 px-4 py-2.5 border border-tgpc-gray-border rounded-full text-[0.875rem] bg-tgpc-bg outline-none focus:border-tgpc-green focus:ring-3 focus:ring-tgpc-green/20 transition-all max-sm:text-base"
    />
    <div class="flex gap-2 flex-wrap">
      <button onclick={onSearch} disabled={query.trim().length < 3}
        class="px-4 py-2 rounded-full text-[0.8125rem] font-medium transition-colors cursor-pointer border-none disabled:opacity-50 disabled:cursor-not-allowed"
        style="background:{query.trim().length >= 3 ? '#00cc66' : '#d1d5db'};color:#fff">
        {loading ? 'Searching…' : 'Search'}
      </button>
      <button onclick={onReset}
        class="px-4 py-2 rounded-full text-[0.8125rem] font-medium bg-gray-200 text-tgpc-text-secondary hover:bg-tgpc-bg-hover transition-colors cursor-pointer border-none">
        Reset
      </button>
    </div>
  </div>
</div>
