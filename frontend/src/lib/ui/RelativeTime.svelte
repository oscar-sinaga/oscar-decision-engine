<script lang="ts">
	import { formatRelativeTime } from './time';
	let { value }: { value: string } = $props();
	const exact = $derived(new Date(value).toISOString());
</script>

<time datetime={value} title={exact}>{formatRelativeTime(value)}</time>
