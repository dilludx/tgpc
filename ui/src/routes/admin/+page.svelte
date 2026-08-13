<script lang="ts">
  import type { PageData } from './$types';
  import type { QuotaReport } from '$lib/types';

  let { data } = $props<{ data: PageData }>();

  const base = 'https://www.pharmacycouncil.telangana.gov.in';

  interface LinkItem {
    heading: string;
    url: string;
    desc: string;
  }

  interface LinkGroup {
    name: string;
    items: LinkItem[];
  }

  const groups: LinkGroup[] = [
    {
      name: 'Search & Profile',
      items: [
        { heading: 'Pharmacist Detail View', url: `${base}/pharmacy/viewpharmacist?referenceid=5428UN062011&random_no1=MMD6XSDJ8LL9`, desc: 'View individual pharmacist profile with full details' },
        { heading: 'Pharmacist Search (POST)', url: `${base}/pharmacy/getsearchpharmacist`, desc: 'Search endpoint — POST registration_no to get results' },
        { heading: 'Admin Dashboard', url: `${base}/pharmacy/dashboard`, desc: 'TGPC admin dashboard' },
      ],
    },
    {
      name: 'Document Management',
      items: [
        { heading: 'Upload Rejected Docs', url: `${base}/pharmacy/editupload_rejected_docs`, desc: 'Form to upload documents that were rejected' },
        { heading: 'Rejected Docs API (POST)', url: `${base}/pharmacy/getrejecteddocsupload`, desc: 'API endpoint for rejected document uploads' },
        { heading: 'BillDesk TID Excel Upload', url: `${base}/site/billdesk_tid_excelreport_upload`, desc: 'Upload BillDesk TID Excel reports' },
      ],
    },
    {
      name: 'Workflow & Tracking',
      items: [
        { heading: 'Workflow Status', url: `${base}/pharmacy/workflowstatus`, desc: 'Detailed workflow tracking for applications' },
        { heading: 'Workflow Info API (POST)', url: `${base}/pharmacy/workflowstatusinfo.action`, desc: 'API endpoint for workflow status information' },
      ],
    },
    {
      name: 'Payments & Verification',
      items: [
        { heading: 'Payment Status Check', url: `${base}/pharmacy/getpmentstatusmeseva`, desc: 'Check payment status via Meseva' },
        { heading: 'Email Verify', url: `${base}/pharmacy/getemailverify?rid1=661JCM272512&rid2=ACPYI0K3KLQJ&rid3=f7b3fdc6-e2f0-4983-a281-d89a26569e02`, desc: 'Verify pharmacist email with verification tokens' },
      ],
    },
    {
      name: 'Reports & Admin',
      items: [
        { heading: 'Dispatch List Report', url: `${base}/pharmacy/dispatchlistreprt`, desc: 'View dispatch list report' },
        { heading: 'Admin Console', url: `${base}/aconsole/adminconsole`, desc: 'TGPC admin console panel' },
      ],
    },
  ];

  let secret = $state('');
  let show = $state(false);
  let authed = $state(false);
  let error = $state('');
  let loading = $state(false);
  let tab = $state<'quota' | 'links'>('quota');
  let report = $state<QuotaReport | null>(data.report);

  if (import.meta.env.DEV) {
    authed = true;
  }

  function barColor(pct: string): string {
    const n = parseFloat(pct);
    if (isNaN(n)) return '#e5e7eb';
    if (n > 90) return '#ef4444';
    if (n > 70) return '#f59e0b';
    return '#00cc66';
  }

  async function login() {
    if (!secret.trim()) return;
    loading = true;
    error = '';
    try {
      const r = await fetch('/api/quota', {
        headers: { 'x-quota-secret': secret.trim() }
      });
      if (r.status === 403) {
        error = 'Wrong password';
        loading = false;
        return;
      }
      if (r.ok) {
        authed = true;
        report = await r.json();
      } else {
        error = 'Server error';
      }
    } catch {
      error = 'Connection error';
    }
    loading = false;
  }

  let copied = $state('');

  async function copyUrl(url: string) {
    try {
      await navigator.clipboard.writeText(url);
      copied = url;
      setTimeout(() => { copied = ''; }, 2000);
    } catch {}
  }

  function logout() {
    authed = false;
    secret = '';
    tab = 'quota';
  }

  let panelHeight = $state(0);

  function measure(section: HTMLDivElement): { destroy: () => void } | void {
    const update = () => {
      const main = document.querySelector('main');
      if (main) {
        const bottom = main.getBoundingClientRect().bottom;
        const pb = parseFloat(getComputedStyle(main).paddingBottom) || 0;
        panelHeight = Math.max(0, Math.floor(bottom - pb - section.getBoundingClientRect().top));
      } else {
        panelHeight = Math.max(0, Math.floor(window.innerHeight - section.getBoundingClientRect().top));
      }
    };
    update();
    window.addEventListener('resize', update);
    return { destroy: () => window.removeEventListener('resize', update) };
  }
</script>

<svelte:head>
  <title>Admin — TGPC RPh Registry</title>
</svelte:head>

<div use:measure style="height:{panelHeight}px;overflow:hidden;display:flex;flex-direction:column">
  {#if !authed}
    <div class="text-center py-16">
      <h1 class="text-2xl font-bold mb-1">Admin</h1>
      <form onsubmit={(e) => { e.preventDefault(); login(); }} class="max-w-xs mx-auto">
        <div class="flex items-center gap-2 border border-[#e5e7eb] rounded focus-within:border-[#00cc66] bg-white">
          <input
            type={show ? 'text' : 'password'}
            bind:value={secret}
            placeholder="Password"
            disabled={loading}
            class="flex-1 outline-none border-none bg-transparent px-3 py-1.5 text-sm min-w-0"
          >
          <button
            type="button"
            onclick={() => show = !show}
            class="shrink-0 px-2 py-1 text-[#6b7280] hover:text-[#00cc66] text-sm"
            aria-label={show ? 'Hide password' : 'Show password'}
            tabindex="-1"
          >{#if show}
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4" aria-hidden="true"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"></path><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"></path><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"></path><line x1="2" x2="22" y1="2" y2="22"></line></svg>
          {:else}
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4" aria-hidden="true"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"></path><circle cx="12" cy="12" r="3"></circle></svg>
          {/if}</button>
        </div>
        <button
          type="submit"
          disabled={loading}
          class="mt-2 w-full bg-[#00cc66] text-white text-sm font-semibold px-4 py-1.5 rounded disabled:opacity-50"
        >{loading ? 'Checking...' : 'Unlock'}</button>
        {#if error}
          <p class="text-xs text-[#ef4444] mt-2">{error}</p>
        {/if}
      </form>
    </div>
  {:else}
    <div class="flex items-center justify-between pb-1">
      <div class="flex items-center gap-0.5" style="font-size:0.7rem;padding-bottom:3px">
        <button style="text-decoration:none;padding:2px 4px;font-weight:700;color:#ef4444;white-space:nowrap;cursor:default;border:none;background:transparent">ADMIN</button>
        <span style="color:#d1d5db;font-weight:300;padding:0;user-select:none">—</span>
        <button onclick={() => tab = 'quota'}
          style="text-decoration:none;padding:2px 4px;font-weight:700;color:{tab === 'quota' ? '#00cc66' : '#6b7280'};white-space:nowrap;cursor:pointer;border:none;background:transparent">FREE TIER USAGE</button>
        <span style="color:#d1d5db;font-weight:300;padding:0;user-select:none">/</span>
        <button onclick={() => tab = 'links'}
          style="text-decoration:none;padding:2px 4px;font-weight:700;color:{tab === 'links' ? '#00cc66' : '#6b7280'};white-space:nowrap;cursor:pointer;border:none;background:transparent">INTERNAL LINKS</button>
      </div>
      <button onclick={logout}
        class="shrink-0 text-xs font-semibold px-3 py-1.5 rounded border border-[#e5e7eb] text-[#6b7280] hover:bg-[#f8f9fa] hover:text-[#ef4444] transition-colors">
        LOGOUT
      </button>
    </div>

    <div style="flex:1;min-height:0;overflow:hidden;display:flex;flex-direction:column">
      {#if tab === 'quota'}
        <div style="flex:1;min-height:0;overflow-y:auto">
          {#if report?.missing_vars?.length}
            <div class="text-xs bg-[#fff3cd] border border-[#ffc107] text-[#856404] rounded px-3 py-2 mb-4">
              <strong>Note:</strong> Some credentials are not configured as Cloudflare Pages environment variables:
              {report.missing_vars.join(', ')}. Set them in the Cloudflare dashboard for live data.
            </div>
          {/if}

          {#each (report?.services ?? []) as service}
            <div class="mb-5 border border-[#e5e7eb] rounded-lg overflow-hidden">
              <div class="bg-[#f8f9fa] px-3 py-2 font-semibold text-sm border-b border-[#e5e7eb]">
                {service.name}
              </div>
              {#if service.error}
                <div class="px-3 py-3 text-xs text-[#ef4444]">{service.error}</div>
              {:else if service.items.length === 0}
                <div class="px-3 py-3 text-xs text-[#9ca3af]">No data available.</div>
              {:else}
                <table class="w-full text-xs">
                  <thead>
                    <tr class="text-left text-[#9ca3af] border-b border-[#e5e7eb]">
                      <th class="px-3 py-1.5 font-medium">Metric</th>
                      <th class="px-3 py-1.5 font-medium text-right">Used</th>
                      <th class="px-3 py-1.5 font-medium text-right">Limit</th>
                      <th class="px-3 py-1.5 font-medium text-center w-28">Usage</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each service.items as item}
                      <tr class="border-b border-[#e5e7eb] last:border-b-0">
                        <td class="px-3 py-1.5">{item.label}</td>
                        <td class="px-3 py-1.5 text-right font-mono">{item.used}</td>
                        <td class="px-3 py-1.5 text-right font-mono">{item.limit ?? '—'}</td>
                        <td class="px-3 py-1.5">
                          <div class="flex items-center gap-2">
                            <div class="flex-1 h-1.5 bg-[#e5e7eb] rounded-full overflow-hidden">
                              {#if item.pct !== '-'}
                                <div class="h-full rounded-full transition-all" style="width:{item.pct};background:{barColor(item.pct)}"></div>
                              {/if}
                            </div>
                            <span class="text-[10px] text-[#6b7280] font-mono w-10 text-right">{item.pct === '-' ? '—' : item.pct}</span>
                          </div>
                        </td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              {/if}
            </div>
          {/each}
        </div>
      {:else}
        <div class="border border-[#e5e7eb] rounded-lg overflow-hidden" style="flex:1;min-height:0;overflow-y:auto;display:flex;flex-direction:column">
          <div class="divide-y divide-[#e5e7eb]" style="flex:1;display:flex;flex-direction:column">
            {#each groups as group}
              <div style="flex:1">
                <div class="bg-[#f8f9fa] px-3 py-2 font-semibold text-sm border-b border-[#e5e7eb] text-[#111827]">
                  {group.name}
                </div>
                <div class="divide-y divide-[#e5e7eb]">
                  {#each group.items as item}
                    <div class="flex items-center gap-2 px-3 py-1.5">
                      <span class="flex-1 text-xs font-mono text-[#2563eb] break-all">{item.url}</span>
                      <button
                        onclick={() => copyUrl(item.url)}
                        class="shrink-0 text-xs font-semibold px-2 py-1 rounded border border-[#e5e7eb] text-[#6b7280] hover:bg-[#f8f9fa] transition-colors"
                      >{copied === item.url ? 'Copied!' : 'Copy'}</button>
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        class="shrink-0 bg-[#00cc66] text-white text-xs font-semibold px-2 py-1 rounded hover:bg-[#00b359] transition-colors"
                      >Open <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-3 h-3 inline" aria-hidden="true"><path d="M15 3h6v6"></path><path d="M10 14 21 3"></path><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path></svg></a>
                    </div>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>