<script lang="ts">
  import { onMount } from 'svelte';

  const MONTHS = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
  let now = $state(new Date());

  onMount(() => {
    const id = setInterval(() => now = new Date(), 1000);
    return () => clearInterval(id);
  });

  let dateStr = $derived(`${String(now.getDate()).padStart(2,'0')} ${MONTHS[now.getMonth()]} ${now.getFullYear()}`);
  let timeStr = $derived(`${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`);
</script>

<span class="opacity-40 leading-[18px]">|</span>
<span class="opacity-80 leading-[18px] tabular-nums whitespace-nowrap">{dateStr} {timeStr}</span>
