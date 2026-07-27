<svelte:head>
  <title>Internal — TGPC RPh Registry</title>
</svelte:head>

<script lang="ts">
  import { browser } from '$app/environment';

  const STORAGE_KEY = 'tgpc_internal_secret';
  const PASSWORD = 'internal';

  interface LinkItem {
    heading: string;
    url: string;
    desc: string;
  }

  interface LinkGroup {
    name: string;
    items: LinkItem[];
  }

  let secret = $state('');
  let authed = $state(browser && sessionStorage.getItem(STORAGE_KEY) !== null);
  let error = $state('');
  let loading = $state(false);

  function login() {
    if (!secret.trim()) return;
    loading = true;
    error = '';
    if (secret.trim() === PASSWORD) {
      sessionStorage.setItem(STORAGE_KEY, secret.trim());
      authed = true;
    } else {
      error = 'Wrong password';
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
    sessionStorage.removeItem(STORAGE_KEY);
    authed = false;
    secret = '';
  }

  const base = 'https://www.pharmacycouncil.telangana.gov.in';

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
</script>

<div class="py-6 px-4">
  {#if !authed}
    <div class="text-center py-16">
      <div class="text-3xl mb-2">🔗</div>
      <h1 class="text-2xl font-bold mb-1">Internal Links</h1>
      <p class="text-xs text-[#6b7280] mb-6">Enter the internal password to access TGPC admin links.</p>
      <form onsubmit={(e) => { e.preventDefault(); login(); }} class="max-w-xs mx-auto">
        <div class="flex gap-2 items-center">
          <input
            type="password"
            bind:value={secret}
            placeholder="Password"
            class="border border-[#e5e7eb] rounded px-3 py-1.5 text-sm flex-1 outline-none focus:border-[#00cc66]"
            disabled={loading}
          >
          <button
            type="submit"
            disabled={loading}
            class="bg-[#00cc66] text-white text-sm font-semibold px-4 py-1.5 rounded disabled:opacity-50"
          >{loading ? 'Checking...' : 'Unlock'}</button>
        </div>
        {#if error}
          <p class="text-xs text-[#ef4444] mt-2">{error}</p>
        {/if}
      </form>
    </div>
  {:else}
    <div class="flex items-center justify-between mb-4">
      <div>
        <div class="text-2xl mb-1">🔗</div>
        <h1 class="text-2xl font-bold">Internal Links</h1>
        <p class="text-xs text-[#6b7280]">TGPC internal admin tools &amp; endpoints</p>
      </div>
      <button onclick={logout} class="text-xs text-[#6b7280] hover:text-[#ef4444] underline">Logout</button>
    </div>

    <div class="space-y-4">
      {#each groups as group}
        <div class="border border-[#e5e7eb] rounded-lg">
          <div class="bg-[#f8f9fa] px-3 py-2 font-semibold text-sm border-b border-[#e5e7eb] text-[#111827]">
            {group.name}
          </div>
          <div class="divide-y divide-[#e5e7eb]">
            {#each group.items as item}
              <div class="flex items-center gap-2 px-3 py-1.5">
                <span class="flex-1 text-xs font-mono text-[#2563eb] whitespace-nowrap">{item.url}</span>
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

    <p class="text-xs text-[#9ca3af] text-center mt-6">
      All links open in new tab &middot; Powered by TGPC RPh Registry
    </p>
  {/if}
</div>
