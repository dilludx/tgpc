<script lang="ts">
  let { query, onSearch, onReset, searching, loading } = $props<{
    query: string;
    onSearch: () => void;
    onReset: () => void;
    searching: boolean;
    loading: boolean;
  }>();
</script>

<div class="space-y-3">
  <h2 class="text-[1.4rem] font-bold tracking-tight">
    <span class="text-tgpc-gray-light">Search</span>
    <span style="color:#ef4444">Rx</span>
  </h2>

  <div class="flex flex-col sm:flex-row gap-2.5">
    <div class="flex-1 relative">
      <svg class="absolute left-4 top-1/2 -translate-y-1/2 w-4.5 h-4.5 text-tgpc-gray-muted pointer-events-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
      </svg>
      <input
        type="text"
        bind:value={query}
        onkeydown={(e) => e.key === 'Enter' && onSearch()}
        placeholder="Name or Registration Number"
        aria-label="Search query"
        class="w-full pl-11 pr-4 py-3 border-2 border-tgpc-gray-border rounded-2xl text-[0.95rem] bg-white outline-none transition-all max-sm:text-base font-medium"
        style="box-shadow:0 2px 4px rgba(0,0,0,0.02)"
        onfocus={(e) => { e.currentTarget.style.borderColor = '#00cc66'; e.currentTarget.style.boxShadow = '0 0 0 4px #00cc6620'; }}
        onblur={(e) => { e.currentTarget.style.borderColor = ''; e.currentTarget.style.boxShadow = ''; }}
      />
    </div>
    <div class="flex gap-2">
      <button onclick={onSearch} disabled={query.trim().length < 3}
        class="px-6 py-3 rounded-2xl text-[0.9rem] font-bold transition-all cursor-pointer border-none disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.97]"
        style="background:{query.trim().length >= 3 ? '#00cc66' : '#d1d5db'};color:#fff;box-shadow:{query.trim().length >= 3 ? '0 4px 12px #00cc6640' : 'none'}">
        {loading ? 'Searching…' : 'Search'}
      </button>
      <button onclick={onReset}
        class="px-5 py-3 rounded-2xl text-[0.85rem] font-semibold bg-white text-tgpc-text-secondary border-2 border-tgpc-gray-border hover:bg-gray-50 hover:border-gray-300 transition-all cursor-pointer active:scale-[0.97]">
        Reset
      </button>
    </div>
  </div>
</div>
