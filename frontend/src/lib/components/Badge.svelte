<script lang="ts">
	import StatusBadge from '$lib/ui/StatusBadge.svelte';

	let {
		value,
		kind = 'status'
	}: {
		value: string;
		kind?: 'decision' | 'status';
	} = $props();
</script>

<span class="contents" data-badge-kind={kind}>
	<StatusBadge {value} />
</span>
