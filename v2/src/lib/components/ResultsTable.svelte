<script lang="ts">
  import type { PharmacistRecord, Category } from '$lib/types';
  import { escapeHtml } from '$lib/utils';

  let { records } = $props<{ records: PharmacistRecord[] }>();

  const badgeColors: Record<Category, { bg: string; text: string }> = {
    BPharm: { bg: '#dcfce7', text: '#166534' },
    DPharm: { bg: '#fef9c3', text: '#854d0e' },
    MPharm: { bg: '#ede9fe', text: '#5b21b6' },
    PharmD: { bg: '#fecaca', text: '#991b1b' },
    QC: { bg: '#dbeafe', text: '#1e40af' },
    QP: { bg: '#fed7aa', text: '#9a3412' }
  };
</script>

<table class="w-full text-[0.9rem] border-separate border-spacing-0" aria-label="Search results">
  <thead>
    <tr class="text-[0.7rem] uppercase font-bold tracking-wider text-tgpc-gray-muted">
      <th class="text-left py-3 px-4" scope="col">Reg No.</th>
      <th class="text-left py-3 px-4" scope="col">Name</th>
      <th class="text-left py-3 px-4 hidden sm:table-cell" scope="col">Father's Name</th>
      <th class="text-left py-3 px-4" scope="col">Category</th>
    </tr>
  </thead>
  <tbody class="stagger">
    {#each records as result, i (result.registration_number)}
      <tr class="bg-white transition-all hover:bg-[#00cc66]/[0.04]"
          style="animation-delay:{i * 30}ms">
        <td class="py-3 px-4 font-semibold text-tgpc-blue rounded-l-xl border-y border-l border-tgpc-gray-border">{escapeHtml(result.registration_number)}</td>
        <td class="py-3 px-4 border-y border-tgpc-gray-border">{escapeHtml(result.name)}</td>
        <td class="py-3 px-4 text-tgpc-text-secondary hidden sm:table-cell border-y border-tgpc-gray-border">{escapeHtml(result.father_name || '—')}</td>
        <td class="py-3 px-4 rounded-r-xl border-y border-r border-tgpc-gray-border">
          <span class="inline-block px-3 py-1 text-[0.75rem] font-bold rounded-lg"
                style="background:{badgeColors[result.category].bg};color:{badgeColors[result.category].text}">
            {result.category}
          </span>
        </td>
      </tr>
    {:else}
      <tr>
        <td colspan="4" class="text-center py-12 text-tgpc-gray-muted">No results</td>
      </tr>
    {/each}
  </tbody>
</table>
