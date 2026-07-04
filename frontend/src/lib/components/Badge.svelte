<script lang="ts">
	import { decisionBadgeClass, statusBadgeClass } from '$lib/format';

	let { value, kind = 'status' }: { value: string; kind?: 'decision' | 'status' } = $props();

	const cls = $derived(kind === 'decision' ? decisionBadgeClass(value) : statusBadgeClass(value));
</script>

<span class="inline-block rounded px-2 py-0.5 text-xs font-semibold whitespace-nowrap {cls}">
	{value.replaceAll('_', ' ')}
</span>
