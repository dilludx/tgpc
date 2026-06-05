<script lang="ts">
  import type { PharmacistRecord } from '$lib/types';
  import { generateCSV, generatePDF } from '$lib/export';

  let { records, keyword }: { records: PharmacistRecord[]; keyword: string } = $props();
</script>

<div class="flex gap-2">
  <button onclick={() => generatePDF(records, keyword)}
    disabled={records.length === 0}
    class="px-4 py-2 rounded-full text-[0.8125rem] font-medium transition-colors cursor-pointer border-none disabled:opacity-40 disabled:cursor-not-allowed"
    style="background:{records.length > 0 ? 'var(--color-tgpc-bg)' : '#f3f4f6'};color:{records.length > 0 ? 'var(--color-tgpc-text)' : '#9ca3af'}">
    PDF
  </button>
  <button onclick={() => generateCSV(records, keyword)}
    disabled={records.length === 0}
    class="px-4 py-2 rounded-full text-[0.8125rem] font-medium transition-colors cursor-pointer border-none disabled:opacity-40 disabled:cursor-not-allowed"
    style="background:{records.length > 0 ? 'var(--color-tgpc-bg)' : '#f3f4f6'};color:{records.length > 0 ? 'var(--color-tgpc-text)' : '#9ca3af'}">
    CSV
  </button>
</div>
