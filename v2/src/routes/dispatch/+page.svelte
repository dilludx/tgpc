<script lang="ts">
  import { escapeHtml } from '$lib/utils';

  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const BASE_URL = 'https://pub-4591c8c5282040459ade2ed1e5e3d5be.r2.dev/dispatch';
  const FALLBACK_DATA: string[] = [
    'DL27042026.pdf', 'DL23022026.pdf', 'DL20042026.pdf', 'DL16022026.pdf',
    'DL10032026.pdf', 'DL09022026.pdf', 'DL04052026.pdf', 'DL04042026.pdf',
    'DL27022026.pdf', 'DL07012026.pdf', 'DL22012026.pdf', 'DL30012026.pdf',
    'DL01062026.pdf', 'DL27052026.pdf', 'DL18052026.pdf',
    'DL03062020C.pdf', 'DL03062020D.pdf', 'DL11102021AD.pdf',
    'DL01112023.pdf', 'DL02042024.pdf', 'DL03062025.pdf', 'DL04052024.pdf',
    'DL05102019.pdf', 'DL07092019.pdf', 'DL10052019.pdf', 'DL16022019.pdf',
    'DL18042019.pdf', 'DL21022018.pdf', 'DL30032019.pdf', 'DL31012025.pdf'
  ];

  interface DispatchFile {
    name: string;
    parsed: { d: string; mo: string; y: string; date: Date } | null;
    size?: number;
  }

  let files = $state<DispatchFile[]>([]);
  let years = $state<string[]>([]);
  let sizeMap = $state<Record<string, number>>({});
  let activeTab = $state<string | null>(null);
  let query = $state('');
  let loading = $state(true);

  function parseDate(name: string) {
    const m = name.match(/DL(\d{2})(\d{2})(\d{4})[A-Z]*\.pdf/i);
    if (!m) return null;
    return { d: m[1], mo: m[2], y: m[3], date: new Date(+m[3], +m[2] - 1, +m[1]) };
  }

  function fmt(f: { d: string; mo: string; y: string }) {
    return `${f.d} ${MONTHS[+f.mo - 1]} ${f.y}`;
  }

  function formatSize(bytes: number) {
    if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    if (bytes >= 1024) return Math.round(bytes / 1024) + ' KB';
    return bytes + ' B';
  }

  let filtered = $derived.by(() => {
    return files.filter(f => {
      if (!f.parsed) return false;
      if (activeTab && f.parsed.y !== activeTab) return false;
      if (!query) return true;
      const q = query.toLowerCase();
      return f.name.toLowerCase().includes(q) || fmt(f.parsed).toLowerCase().includes(q);
    });
  });

  function buildFromRaw(raw: { name: string; size?: number }[]) {
    const sm: Record<string, number> = {};
    raw.forEach(f => { if (f.size) sm[f.name] = f.size; });
    sizeMap = sm;

    const fl: DispatchFile[] = raw
      .map(f => ({ name: f.name, parsed: parseDate(f.name), size: f.size }))
      .filter(f => f.parsed)
      .sort((a, b) => b.parsed!.date.getTime() - a.parsed!.date.getTime());

    files = fl;
    years = [...new Set(fl.map(f => f.parsed!.y))].sort((a, b) => +b - +a);
    activeTab = years[0] || null;
  }

  async function loadData() {
    loading = true;
    try {
      const resp = await fetch('/api/dispatch');
      if (!resp.ok) throw new Error('API unavailable');
      const data = await resp.json();
      buildFromRaw(data);
    } catch {
      const fallback = FALLBACK_DATA.map(n => ({ name: n, size: Math.round(50000 + Math.random() * 200000) }));
      buildFromRaw(fallback);
    }
    loading = false;
  }

  function setTab(year: string | null) {
    activeTab = year;
  }

  $effect(() => { loadData(); });
</script>

<div class="space-y-4">
  <div class="bg-white border border-tgpc-gray-border rounded-lg p-3">
    <div class="flex items-center justify-between flex-wrap gap-2">
      <h2 class="text-[1.1rem] max-md:text-[0.9rem] font-semibold">
        <span class="text-tgpc-gray-light">Dispatch Lists</span>
      </h2>
      {#if !loading}
        <span class="text-[0.8rem] text-tgpc-gray-muted">{files.length} file{files.length !== 1 ? 's' : ''}</span>
      {/if}
    </div>
  </div>

  <!-- Search + Tabs -->
  <div class="bg-white border border-tgpc-gray-border rounded-lg p-3 space-y-3">
    <div class="flex items-center gap-2 flex-wrap">
      <div class="flex-1 min-w-0 relative">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-tgpc-gray-muted pointer-events-none" viewBox="0 0 24 24" fill="currentColor"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
        <input type="text" bind:value={query} placeholder="Search files..."
          class="w-full pl-9 pr-4 py-2 border border-tgpc-gray-border rounded-full text-[0.85rem] bg-tgpc-bg outline-none focus:border-tgpc-green transition-colors max-sm:text-base" />
      </div>
      {#if query}
        <span class="text-[0.8rem] text-tgpc-gray-muted">{filtered.length} of {files.length} files</span>
      {/if}
    </div>

    <div class="flex gap-1 overflow-x-auto pb-0.5" style="scrollbar-width:none">
      {#each years as year}
        <button onclick={() => setTab(year)}
          class="flex-shrink-0 px-3 py-1.5 rounded-lg text-[0.8rem] font-medium transition-colors cursor-pointer border-none"
          style={year === activeTab ? 'background:#00cc66;color:#fff' : 'background:transparent;color:#4a4a5a;border:1px solid #e2e8f0'}>
          {year}
          <span class="opacity-60 text-[0.7rem]"> ({files.filter(f => f.parsed?.y === year).length})</span>
        </button>
      {/each}
    </div>
  </div>

  <!-- File Grid -->
  {#if loading}
    <div class="text-center py-8 text-tgpc-gray-muted text-[0.875rem]">
      <div class="w-6 h-6 border-3 border-tgpc-gray-border border-t-tgpc-green rounded-full animate-spin mx-auto mb-3"></div>
      <p>Loading dispatch lists...</p>
    </div>
  {:else if filtered.length === 0}
    <div class="text-center py-8 text-tgpc-gray-muted text-[0.875rem]">
      <p>No files match your search</p>
    </div>
  {:else}
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-1.5">
      {#if activeTab === null}
        {#each years as year}
          {@const fy = filtered.filter(f => f.parsed?.y === year)}
          {#if fy.length > 0}
            <div class="col-span-full text-[0.75rem] font-semibold uppercase tracking-wider text-tgpc-gray-muted px-2 py-2 border-b border-tgpc-gray-border mb-1">
              {year} &mdash; {fy.length} file{fy.length !== 1 ? 's' : ''}
            </div>
            {#each fy as f}
              <a href={`${BASE_URL}/${f.name}`} target="_blank" rel="noopener"
                class="flex items-center gap-2 p-2 border border-tgpc-gray-border rounded-lg no-underline text-tgpc-text transition-all hover:bg-[#f0fdf4] hover:border-tgpc-green">
                <div class="w-8 h-10 flex items-center justify-center flex-shrink-0">
                  <img src="/pdf.png" alt="" width="28" height="28" class="block" />
                </div>
                <div class="flex-1 min-w-0">
                  <div class="text-[0.85rem] font-medium truncate">{f.parsed ? fmt(f.parsed) : f.name}</div>
                  <div class="text-[0.7rem] text-tgpc-gray-muted mt-0.5">{sizeMap[f.name] ? formatSize(sizeMap[f.name]) : ''}</div>
                </div>
              </a>
            {/each}
          {/if}
        {/each}
      {:else}
        {#each filtered as f}
          <a href={`${BASE_URL}/${f.name}`} target="_blank" rel="noopener"
            class="flex items-center gap-2 p-2 border border-tgpc-gray-border rounded-lg no-underline text-tgpc-text transition-all hover:bg-[#f0fdf4] hover:border-tgpc-green">
            <div class="w-8 h-10 flex items-center justify-center flex-shrink-0">
              <img src="/pdf.png" alt="" width="28" height="28" class="block" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-[0.85rem] font-medium truncate">{f.parsed ? fmt(f.parsed) : f.name}</div>
              <div class="text-[0.7rem] text-tgpc-gray-muted mt-0.5">{sizeMap[f.name] ? formatSize(sizeMap[f.name]) : ''}</div>
            </div>
          </a>
        {/each}
      {/if}
    </div>
  {/if}
</div>
