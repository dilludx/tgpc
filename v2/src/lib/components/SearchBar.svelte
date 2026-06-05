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
  <h2 class="text-[1.15rem] font-semibold">
    <span class="text-tgpc-gray-light">Search</span>
    <span style="color:#ef4444">Rx</span>
  </h2>

  <div class="flex flex-col sm:flex-row gap-2">
    <div class="flex-1 relative">
      <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-tgpc-gray-muted pointer-events-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
      </svg>
      <input
        type="text"
        bind:value={query}
        onkeydown={(e) => e.key === 'Enter' && onSearch()}
        placeholder="Name or Registration Number"
        aria-label="Search query"
        class="w-full pl-9 pr-4 py-2.5 border border-tgpc-gray-border rounded-xl text-[0.875rem] bg-white outline-none transition-all max-sm:text-base"
        style="box-shadow:0 1px 2px rgba(0,0,0,0.02)"
        onfocus={(e) => { e.currentTarget.style.borderColor = '#00cc66'; e.currentTarget.style.boxShadow = '0 0 0 3px #00cc6620'; }}
        onblur={(e) => { e.currentTarget.style.borderColor = ''; e.currentTarget.style.boxShadow = ''; }}
      />
    </div>
    <div class="flex gap-2">
      <button onclick={onSearch} disabled={query.trim().length < 3}
        class="px-5 py-2.5 rounded-xl text-[0.8125rem] font-semibold transition-all cursor-pointer border-none disabled:opacity-50 disabled:cursor-not-allowed active:scale-95"
        style="background:{query.trim().length >= 3 ? '#00cc66' : '#d1d5db'};color:#fff;box-shadow:{query.trim().length >= 3 ? '0 2px 6px #00cc6640' : 'none'}">
        {loading ? 'Searching…' : 'Search'}
      </button>
      <button onclick={onReset}
        class="px-4 py-2.5 rounded-xl text-[0.8125rem] font-medium bg-gray-100 text-tgpc-text-secondary hover:bg-gray-200 transition-all cursor-pointer border-none active:scale-95">
        Reset
      </button>
    </div>
  </div>
</div>
