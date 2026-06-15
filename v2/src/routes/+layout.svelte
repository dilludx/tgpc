<script lang="ts">
  import '../app.css';
  import type { ConnectionStatus, Stats } from '$lib/types';
  import { getStats } from '$lib/api';
  import { supabase } from '$lib/supabase';
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { CATEGORY_COLORS, CATEGORIES, CATEGORY_KEYS } from '$lib/colors';

  let { children } = $props();

  let status = $state<ConnectionStatus>('Busy');
  let stats = $state<Stats | null>(null);
  let lastSync = $state<string>('');
  let tick = $state(0);

  const MONTHS = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];

  let dateStr = $derived.by(() => {
    tick;
    const d = new Date();
    return `${String(d.getDate()).padStart(2,'0')} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
  });
  let timeStr = $derived.by(() => {
    tick;
    const d = new Date();
    return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`;
  });
  let year = $derived.by(() => { tick; return new Date().getFullYear(); });

  async function loadStats() {
    status = 'Busy';
    const data = await getStats();
    if (data) {
      stats = data;
      status = 'Live';
    } else {
      status = 'Offline';
    }
  }

  async function loadLastSync() {
    try {
      const { data, error } = await supabase
        .from('metadata')
        .select('value')
        .eq('key', 'last_sync')
        .single();
      if (!error && data?.value) {
        const d = new Date(data.value);
        const s = d.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', weekday: 'short', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
        lastSync = s.toUpperCase().replace(/,/g, '');
      }
    } catch {}
  }

  $effect(() => {
    loadStats();
    loadLastSync();
    const id = setInterval(loadStats, 300_000);
    return () => clearInterval(id);
  });

  onMount(() => {
    tick = Date.now();
    const id = setInterval(() => tick = Date.now(), 1000);
    return () => clearInterval(id);
  });

  let statusConfig = $derived.by(() => ({
    Live: { bg: 'rgba(34,197,94,0.05)', border: '#86efac', text: '#166534', dot: '#22c55e' },
    Busy: { bg: 'rgba(239,68,68,0.05)', border: '#fca5a5', text: '#991b1b', dot: '#ef4444' },
    Offline: { bg: 'rgba(239,68,68,0.05)', border: '#fca5a5', text: '#991b1b', dot: '#ef4444' }
  })[status]);

  function val(key: keyof Stats): string {
    return stats ? stats[key].toLocaleString() : '—';
  }

  let activeTab = $derived($page.url.pathname === '/' ? 'search' : $page.url.pathname === '/notice' ? 'notice' : 'dispatch');

  let searchRef: HTMLAnchorElement | undefined;
  let noticeRef: HTMLAnchorElement | undefined;
  let dispatchRef: HTMLAnchorElement | undefined;
  let sliderStyle = $state('');
  let headingEl: HTMLAnchorElement | undefined;
  let headingWidth = $state(0);

  $effect(() => {
    if (!headingEl) return;
    const ro = new ResizeObserver(entries => {
      for (const entry of entries) {
        headingWidth = entry.contentRect.width;
      }
    });
    ro.observe(headingEl);
    return () => ro.disconnect();
  });

  $effect(() => {
    const tab = activeTab;
    let el = tab === 'search' ? searchRef : tab === 'notice' ? noticeRef : dispatchRef;
    if (el) {
      sliderStyle = `transform:translateX(${el.offsetLeft}px);width:${el.offsetWidth}px`;
    }
  });
</script>
<div class="h-screen flex flex-col bg-white overflow-hidden">
  <header class="sticky top-0 z-50 bg-white">
    <div class="w-full px-4 sm:px-6 py-2.5 flex items-center justify-between gap-4">
      <div class="flex flex-col gap-0.5" style={headingWidth ? `width:${headingWidth}px` : ''}>
        <a href="/" bind:this={headingEl} class="no-underline inline-flex flex-col w-fit">
          <span class="text-[1.4rem] font-bold tracking-tight flex items-center gap-1" style="color:#111;white-space:nowrap">
            <span style="color:#00cc66">TGPC</span><span style="color:#ef4444">RPh</span><span class="text-[#9ca3af]">Registry</span>
          </span>
          <span class="block text-[0.6rem] text-[#9ca3af] font-medium truncate">Open-Source TGPC Pharmacist Data</span>
        </a>
        <div class="flex items-center gap-2 text-[0.7rem]">
          <span class="flex w-full items-center gap-1 h-5 px-1.5 rounded-full text-[0.625rem] font-medium"
                style="background:{statusConfig.bg};border:1px solid {statusConfig.border};color:{statusConfig.text}">
            <span class="w-1.5 h-1.5 rounded-full flex-shrink-0" style="background:{statusConfig.dot}"></span>
            <span class="text-[10px] font-medium leading-[18px]">{status}</span>
            <span class="opacity-40 leading-[18px]">|</span>
            <span class="opacity-80 leading-[18px] tabular-nums whitespace-nowrap">{dateStr} {timeStr}</span>
          </span>
        </div>
      </div>
      <div style="background:#f8f9fa;border:1px solid #e5e7eb;border-radius:8px;padding:6px 10px 4px 10px;display:flex;flex-direction:column;gap:0;flex-shrink:0">
        <div style="display:flex;gap:10px;align-items:center">
          <div style="border-right:1px solid #e5e7eb;padding-right:12px">
            <div style="display:flex;flex-direction:column;gap:4px">
              <div style="font-size:0.6875rem;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;color:#808080">Total <span style="color:#ef4444;text-transform:none">RPh</span></div>
              <div style="font-size:1.25rem;font-weight:700;color:#1a1a1a;line-height:1;font-variant-numeric:tabular-nums">{val('total')}</div>
            </div>
          </div>
          {#each CATEGORIES as cat, i}
            <div style="border-right:{i < 5 ? '1px solid #e5e7eb' : 'none'};padding-right:{i < 5 ? '12px' : '0'}">
              <div style="display:flex;flex-direction:column;gap:4px">
                <div style="font-size:0.6875rem;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;color:{CATEGORY_COLORS[cat]}">{cat}</div>
                <div style="font-size:1.25rem;font-weight:700;color:#1a1a1a;line-height:1;font-variant-numeric:tabular-nums">{val(CATEGORY_KEYS[i] as keyof Stats)}</div>
              </div>
            </div>
          {/each}
        </div>
        <div style="font-size:0.5rem;color:#a1a1aa;font-weight:500;letter-spacing:0.3px;text-transform:uppercase;margin-top:4px;padding-top:4px;border-top:1px solid #e5e7eb;display:flex;align-items:center;gap:6px;flex-wrap:wrap">
          <span style="display:inline-flex;align-items:center;gap:3px;background:rgba(0,204,102,0.1);padding:1px 6px 1px 4px;border-radius:10px">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:10px;height:10px;background:#00cc66;border-radius:50%;color:white;font-size:6px;font-weight:bold">&#10003;</span>
            <span style="color:#00cc66;font-size:0.45rem;font-weight:600;text-transform:uppercase;letter-spacing:0.3px">Synced</span>
          </span>
          <span style="background:linear-gradient(135deg,#2563eb 0%,#7c3aed 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">{lastSync || `${dateStr} ${timeStr}`}</span>
          <span style="opacity:0.4">|</span>
          <span style="color:#9ca3af">Unofficial data — Not for legal use</span>
        </div>
      </div>
    </div>
    <div class="w-full px-4 sm:px-6 border-b border-[#e5e7eb]" style="display:flex;align-items:center;gap:2px;background:#f8f9fa;font-size:0.7rem;padding-top:3px;padding-bottom:3px;overflow-x:auto;position:relative">
      <a href="/" bind:this={searchRef} style="text-decoration:none;padding:2px 4px;font-weight:500;color:{activeTab === 'search' ? '#00cc66' : '#6b7280'};white-space:nowrap">SEARCH</a>
      <span style="color:#d1d5db;font-weight:300;padding:0 2px;user-select:none">/</span>
      <a href="/notice" bind:this={noticeRef} style="text-decoration:none;padding:2px 4px;font-weight:500;color:{activeTab === 'notice' ? '#00cc66' : '#6b7280'};white-space:nowrap">NOTICES</a>
      <span style="color:#d1d5db;font-weight:300;padding:0 2px;user-select:none">/</span>
      <a href="/dispatch" bind:this={dispatchRef} style="text-decoration:none;padding:2px 4px;font-weight:500;color:{activeTab === 'dispatch' ? '#00cc66' : '#6b7280'};white-space:nowrap">DISPATCH LIST</a>
      <div style="position:absolute;bottom:0;left:0;height:2px;background:#00cc66;border-radius:1px;transition:transform 0.25s ease-out,width 0.25s ease-out;will-change:transform,width;{sliderStyle}"></div>
    </div>
  </header>

  <main class="flex-1 w-full px-4 sm:px-6 pt-1 pb-14 overflow-hidden">
    {@render children()}
  </main>

  <footer class="fixed bottom-0 w-full bg-white border-t border-[#e5e7eb] py-1 text-[0.5rem] text-[#9ca3af] leading-tight"
          style="padding-bottom:calc(0.25rem + env(safe-area-inset-bottom, 0px))">
    <div class="w-full px-4 sm:px-6 flex items-center justify-between gap-4">
      <span class="text-left flex-1 pr-4" style="text-wrap:balance"><span style="color:#ef4444">DISCLAIMER:</span> This is an unofficial, third-party tool not affiliated with TGPC or any government body. Data is for reference only — verify all information from official sources before use. Users assume all risk.<br>No warranty as to accuracy, completeness, or timeliness. No liability for errors, omissions, or actions taken based on this content. Operated under fair dealing (Indian Copyright Act, 1957, Section 52).</span>
      <span class="text-right whitespace-nowrap font-semibold flex-shrink-0 text-[0.7rem]">TGPC RPh Registry &copy; {year}</span>
    </div>
  </footer>
</div>

<style>
  .notice-btn {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    height: 20px;
    padding: 0 7px;
    border-radius: 50px;
    font-size: 0.625rem;
    font-weight: 500;
    color: #7c3aed;
    background: #f3f0ff;
    text-decoration: none;
    transition: background 0.15s;
    box-sizing: border-box;
  }
  .notice-btn:hover {
    background: #e8e3ff;
  }

  .dispatch-btn {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    height: 20px;
    padding: 0 7px;
    border-radius: 50px;
    font-size: 0.625rem;
    font-weight: 500;
    color: #ef4444;
    background: #fef2f2;
    text-decoration: none;
    transition: background 0.15s;
    box-sizing: border-box;
  }
  .dispatch-btn:hover {
    background: #fee2e2;
  }

  .search-btn {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    height: 20px;
    padding: 0 7px;
    border-radius: 50px;
    font-size: 0.625rem;
    font-weight: 500;
    color: #00cc66;
    background: #d9f7eb;
    text-decoration: none;
    transition: background 0.15s;
    box-sizing: border-box;
  }
  .search-btn:hover {
    background: #b3efd6;
  }
</style>
