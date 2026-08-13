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
</script>

<svelte:head>
  <title>Admin — TGPC RPh Registry</title>
</svelte:head>

<div class="py-6" style="height:calc(100dvh - 110px);overflow:hidden;display:flex;flex-direction:column">
  {#if !authed}
    <div class="text-center py-16">
      <h1 class="text-2xl font-bold mb-1 inline-flex items-center gap-2"><span>🔐</span> <span>Admin</span></h1>
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
          >{show ? '🙈' : '👁️'}</button>
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
    <div class="flex items-center justify-between mb-4">
      <div>
        <h1 class="text-2xl font-bold mb-1">Admin</h1>
      </div>
      <button onclick={logout}
        class="shrink-0 text-xs font-semibold px-3 py-1.5 rounded border border-[#e5e7eb] text-[#6b7280] hover:bg-[#f8f9fa] hover:text-[#ef4444] transition-colors">
        Logout
      </button>
    </div>

    <div class="w-full border-b border-[#e5e7eb] mb-4" style="display:flex;align-items:center;gap:2px;font-size:0.7rem;padding-top:3px;padding-bottom:3px;overflow-x:auto">
      <button onclick={() => tab = 'quota'}
        style="text-decoration:none;padding:2px 4px;font-weight:700;color:{tab === 'quota' ? '#00cc66' : '#6b7280'};white-space:nowrap;cursor:pointer;border:none;background:transparent">FREE TIER USAGE</button>
      <span style="color:#d1d5db;font-weight:300;padding:0 2px;user-select:none">/</span>
      <button onclick={() => tab = 'links'}
        style="text-decoration:none;padding:2px 4px;font-weight:700;color:{tab === 'links' ? '#00cc66' : '#6b7280'};white-space:nowrap;cursor:pointer;border:none;background:transparent">INTERNAL LINKS</button>
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
        <div class="border border-[#e5e7eb] rounded-lg overflow-hidden" style="flex:1;min-height:0;overflow-y:auto">
          <div class="divide-y divide-[#e5e7eb]">
            {#each groups as group}
              <div>
                <div class="bg-[#f8f9fa] px-3 py-2 font-semibold text-sm border-b border-[#e5e7eb] text-[#111827] sticky top-0">
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
                      >Open ↗</a>
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