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

<table class="w-full text-[0.875rem]" aria-label="Search results">
  <thead>
    <tr class="text-[0.7rem] uppercase font-semibold tracking-wider text-tgpc-text-secondary border-b border-tgpc-table-border bg-tgpc-bg/50">
      <th class="text-left py-2.5 px-4" scope="col">Registration Number</th>
      <th class="text-left py-2.5 px-4" scope="col">Name</th>
      <th class="text-left py-2.5 px-4 hidden sm:table-cell" scope="col">Father's Name</th>
      <th class="text-left py-2.5 px-4" scope="col">Category</th>
    </tr>
  </thead>
  <tbody class="stagger">
    {#each records as result, i (result.registration_number)}
      <tr class="border-b border-tgpc-table-border transition-colors hover:bg-tgpc-green-light/40"
          style="animation-delay:{i * 30}ms">
        <td class="py-3 px-4 font-medium text-tgpc-blue">{escapeHtml(result.registration_number)}</td>
        <td class="py-3 px-4">{escapeHtml(result.name)}</td>
        <td class="py-3 px-4 text-tgpc-text-secondary hidden sm:table-cell">{escapeHtml(result.father_name || '—')}</td>
        <td class="py-3 px-4">
          <span class="inline-block px-2.5 py-0.5 text-[0.75rem] font-semibold rounded-md"
                style="background:{badgeColors[result.category].bg};color:{badgeColors[result.category].text}">
            {result.category}
          </span>
        </td>
      </tr>
    {:else}
      <tr>
        <td colspan="4" class="text-center py-10 text-tgpc-gray-muted">No results</td>
      </tr>
    {/each}
  </tbody>
</table>
