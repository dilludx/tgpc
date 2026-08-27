<script lang="ts">
  import { CATEGORY_COLORS } from '$lib/colors';
  import type { PharmacistRecord } from '$lib/types';

  let { data } = $props();
  const { record, photo, seo } = data as {
    record: PharmacistRecord;
    photo: string;
    seo: { title: string; description: string; ogImage: string; canonical: string };
  };

  let photoError = $state(false);

  function handlePhotoError() {
    photoError = true;
  }

  function formatDate(dateStr: string | null | undefined): string {
    if (!dateStr) return '—';
    return dateStr;
  }

  function statusColor(status: string | null | undefined): string {
    return status === 'Active' ? '#111827' : '#ef4444';
  }

  function categoryColor(cat: string): string {
    return CATEGORY_COLORS[cat as keyof typeof CATEGORY_COLORS] || '#6b7280';
  }

  function printPage() {
    window.print();
  }

  function backToSearch() {
    window.history.back();
  }
</script>

<svelte:head>
  <title>{seo.title}</title>
  <meta name="description" content={seo.description} />
  <meta property="og:title" content={seo.title} />
  <meta property="og:description" content={seo.description} />
  <meta property="og:image" content={seo.ogImage} />
  <meta property="og:type" content="profile" />
  <meta property="og:url" content={seo.canonical} />
  <link rel="canonical" href={seo.canonical} />
  <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Person",
      "name": "{record.name}",
      "identifier": "{record.registration_number}",
      "description": "{seo.description}",
      "image": "{seo.ogImage}",
      "url": "{seo.canonical}",
      "worksFor": {
        "@type": "Organization",
        "name": "Telangana State Pharmacy Council"
      },
      "jobTitle": "Registered Pharmacist",
      "gender": "{record.gender || ''}",
      "knowsAbout": ["Pharmacy", "{record.category}"]
    }
  </script>
</svelte:head>

<div class="max-w-3xl mx-auto space-y-6 px-4 py-6">
  <div class="flex items-center gap-3 mb-4">
    <button
      onclick={backToSearch}
      class="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#e5e7eb] text-[0.75rem] font-medium text-[#374151] hover:bg-[#f4f4f5] transition-colors"
      aria-label="Back to search"
    >
      <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M19 12H5M12 19l-7-7 7-7" />
      </svg>
      Back to Search
    </button>
  </div>

  <!-- Header Card -->
  <div class="bg-white border border-[#e5e7eb] rounded-xl p-6 space-y-4">
    <div class="flex flex-col md:flex-row gap-6 items-start md:items-center">
      <div class="flex-shrink-0 w-32 h-40 md:w-36 md:h-44 rounded-lg bg-[#f3f4f6] overflow-hidden relative">
        <img
          src={photo}
          alt={`${record.name}'s photo`}
          onerror={handlePhotoError}
          class="w-full h-full object-cover {photoError ? 'hidden' : ''}"
        />
        {#if photoError}
          <div class="w-full h-full flex items-center justify-center bg-[#f3f4f6]">
            <svg class="w-16 h-16 text-[#d1d5db]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </div>
        {/if}
      </div>

      <div class="flex-1 min-w-0 space-y-2">
        <h1 class="text-2xl md:text-3xl font-bold text-[#111827] truncate">{record.name}</h1>

        <div class="flex flex-wrap items-center gap-2.5">
          <span class="px-3 py-1 rounded-full text-[0.7rem] font-semibold uppercase tracking-wider tabular-nums"
            style="background:#2563eb15;color:#2563eb">
            RPC: {record.registration_number}
          </span>
          <span class="px-3 py-1 rounded-full text-[0.7rem] font-semibold uppercase tracking-wider"
            style="background:{categoryColor(record.category)}15;color:{categoryColor(record.category)}">
            {record.category}
          </span>
          <span class="px-3 py-1 rounded-full text-[0.7rem] font-semibold uppercase tracking-wider"
            style="background:{record.status === 'Active' ? 'rgba(0,204,102,0.1)' : 'rgba(239,68,68,0.1)'};color:{statusColor(record.status)}">
            {record.status || 'Unknown'}
          </span>
        </div>

        <div class="flex flex-wrap items-center gap-4 text-[0.875rem] text-[#6b7280]">
          <span>Serial: <span class="text-[#374151] font-medium">#{record.serial_number || '—'}</span></span>
          <span>Valid till: <span class="text-[#374151] font-medium">{formatDate(record.validity_date)}</span></span>
        </div>
      </div>
    </div>

    <div class="border-t border-[#f3f4f6] pt-4 flex flex-wrap gap-4 text-[0.875rem]">
      <div class="flex items-center gap-1.5">
        <span class="text-[#9ca3af]">Father:</span>
        <span class="text-[#374151] font-medium">{record.father_name || '—'}</span>
      </div>
      {#if record.gender}
        <div class="flex items-center gap-1.5">
          <span class="text-[#9ca3af]">Gender:</span>
          <span class="text-[#374151] font-medium">{record.gender}</span>
        </div>
      {/if}
    </div>
  </div>

  <!-- Education Section -->
  {#if record.education && record.education.length > 0}
    <section class="bg-white border border-[#e5e7eb] rounded-xl p-6 space-y-4">
      <h2 class="text-lg font-semibold text-[#111827] flex items-center gap-2">
        <svg class="w-5 h-5 text-[#00cc66]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
          <path d="M6 12v5c3 3 9 3 12 0v-5" />
        </svg>
        Education
      </h2>
      <div class="overflow-x-auto">
        <table class="w-full text-sm" style="table-layout:auto">
          <thead>
            <tr class="text-[0.65rem] font-semibold text-[#9ca3af] uppercase tracking-wider border-b border-[#e5e7eb]">
              <th class="text-left py-2 px-3">Category</th>
              <th class="text-left py-2 px-3">Board / University</th>
              <th class="text-left py-2 px-3">College</th>
              <th class="text-left py-2 px-3 hidden md:table-cell">Address</th>
              <th class="text-left py-2 px-3 hidden lg:table-cell">From – To</th>
              <th class="text-left py-2 px-3">HT No</th>
            </tr>
          </thead>
          <tbody>
            {#each record.education as edu}
              <tr class="border-b border-[#f3f4f6] text-[#374151]">
                <td class="py-2 px-3 font-medium" style="color:{categoryColor(edu.Category || '')}">{edu.Category || '—'}</td>
                <td class="py-2 px-3 truncate max-w-xs" title={edu['Board/University'] || ''}>{edu['Board/University'] || '—'}</td>
                <td class="py-2 px-3 truncate max-w-xs" title={edu['College Name'] || ''}>{edu['College Name'] || '—'}</td>
                <td class="py-2 px-3 truncate max-w-xs hidden md:table-cell" title={edu['College Address'] || ''}>{edu['College Address'] || '—'}</td>
                <td class="py-2 px-3 hidden lg:table-cell">
                  {edu.From || ''}{#if edu.From && edu.To} – {/if}{edu.To || ''}
                  {#if !edu.From && !edu.To}—{/if}
                </td>
                <td class="py-2 px-3 tabular-nums">{edu['HT No'] || '—'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {/if}

  <!-- Work Experience Section -->
  {#if record.work_experience && (record.work_experience.Address || record.work_experience.State || record.work_experience.District || record.work_experience['Pin code'])}
    <section class="bg-white border border-[#e5e7eb] rounded-xl p-6 space-y-3">
      <h2 class="text-lg font-semibold text-[#111827] flex items-center gap-2">
        <svg class="w-5 h-5 text-[#00cc66]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 13.25V21" />
          <path d="M3 9v12" />
          <path d="M12 3v18" />
          <path d="M12 3h15a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-15a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" />
        </svg>
        Work Experience
      </h2>
      <dl class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[0.875rem]">
        <div>
          <dt class="text-[#9ca3af] text-[0.7rem] font-semibold uppercase tracking-wider">Address</dt>
          <dd class="text-[#374151] mt-0.5">{record.work_experience.Address || '—'}</dd>
        </div>
        <div>
          <dt class="text-[#9ca3af] text-[0.7rem] font-semibold uppercase tracking-wider">State</dt>
          <dd class="text-[#374151] mt-0.5">{record.work_experience.State || '—'}</dd>
        </div>
        <div>
          <dt class="text-[#9ca3af] text-[0.7rem] font-semibold uppercase tracking-wider">District</dt>
          <dd class="text-[#374151] mt-0.5">{record.work_experience.District || '—'}</dd>
        </div>
        <div>
          <dt class="text-[#9ca3af] text-[0.7rem] font-semibold uppercase tracking-wider">Pin Code</dt>
          <dd class="text-[#374151] mt-0.5">{record.work_experience['Pin code'] || '—'}</dd>
        </div>
      </dl>
    </section>
  {/if}

  <!-- Actions -->
  <div class="flex items-center justify-end gap-3 pt-2">
    <button
      onclick={printPage}
      class="flex items-center gap-1.5 px-4 py-2 rounded border border-[#e5e7eb] text-[0.75rem] font-medium text-[#374151] hover:bg-[#f4f4f5] transition-colors"
    >
      <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="6 9 6 2 18 2 18 9" />
        <path d="M6 18H4a2 2 0 0 1-2-2v-5" />
        <path d="M18 18h2a2 2 0 0 0 2-2v-5" />
        <rect x="6" y="14" width="12" height="8" />
      </svg>
      Print / Save as PDF
    </button>
  </div>

  <footer class="text-center text-[0.7rem] text-[#9ca3af] py-4 border-t border-[#e5e7eb]">
    Data sourced from Telangana State Pharmacy Council &middot; <a href="https://tgpc.pages.dev" class="text-[#2563eb] hover:underline">tgpc.pages.dev</a>
  </footer>
</div>

<style>
  @media print {
    .no-print { display: none !important; }
    .max-w-3xl { max-width: none !important; padding: 0 !important; }
    .bg-white { box-shadow: none !important; border: 1px solid #e5e7eb !important; break-inside: avoid; }
    button { display: none !important; }
    a { text-decoration: none !important; color: inherit !important; }
  }
</style>