<script lang="ts">
  import type { ConnectionStatus } from '$lib/types';

  let { status }: { status: ConnectionStatus } = $props();

  const config: Record<ConnectionStatus, { bg: string; text: string; dot: string }> = {
    Live: { bg: '#dcfce7', text: '#16a34a', dot: '#00cc66' },
    Busy: { bg: '#f3f4f6', text: '#6b7280', dot: '#9ca3af' },
    Offline: { bg: '#fee2e2', text: '#dc2626', dot: '#ef4444' }
  };
</script>

<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[0.625rem] font-medium"
      style="background:{config[status].bg};color:{config[status].text}">
  <span class="inline-block w-1.5 h-1.5 rounded-full animate-pulse-scale"
        style="background:{config[status].dot}"></span>
  {status}
</span>
