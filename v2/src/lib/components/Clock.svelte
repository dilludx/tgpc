<script lang="ts">
  import { fmtDate, fmtTime } from '$lib/utils';

  let { now }: { now: Date } = $props();
</script>

{fmtDate(now)} {fmtTime(now)}
