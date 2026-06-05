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

<div class="space-y-2 stagger">
  {#each records as result, i (result.registration_number)}
    <article class="card-hover bg-white border border-tgpc-gray-border rounded-xl p-3.5"
             style="animation-delay:{i * 40}ms">
      <div class="flex items-center justify-between mb-1.5">
        <span class="font-semibold text-tgpc-blue text-[0.875rem]">{escapeHtml(result.registration_number)}</span>
        <span class="inline-block px-2.5 py-0.5 text-[0.75rem] font-semibold rounded-md"
              style="background:{badgeColors[result.category].bg};color:{badgeColors[result.category].text}">
          {result.category}
        </span>
      </div>
      <div class="text-[0.875rem] text-tgpc-text font-medium">{escapeHtml(result.name)}</div>
      <div class="text-[0.75rem] text-tgpc-text-secondary mt-0.5">{escapeHtml(result.father_name || '—')}</div>
    </article>
  {:else}
    <div class="text-center py-10 text-tgpc-gray-muted">No results</div>
  {/each}
</div>
