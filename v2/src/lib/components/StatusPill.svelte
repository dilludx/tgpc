<script lang="ts">
  import type { ConnectionStatus } from '$lib/types';

  let { status }: { status: ConnectionStatus } = $props();

  const config: Record<ConnectionStatus, { bg: string; text: string; dot: string; label: string }> = {
    Live: { bg: '#dcfce7', text: '#16a34a', dot: '#00cc66', label: 'Connected' },
    Busy: { bg: '#fff7ed', text: '#9a3412', dot: '#f97316', label: 'Checking…' },
    Offline: { bg: '#fee2e2', text: '#dc2626', dot: '#ef4444', label: 'Disconnected' }
  };
</script>

<span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[0.65rem] font-semibold shadow-sm"
      style="background:{config[status].bg};color:{config[status].text}"
      title={config[status].label}>
  <span class="inline-block w-2 h-2 rounded-full"
        style="background:{config[status].dot};box-shadow:0 0 4px {config[status].dot}40"></span>
  {status}
</span>
