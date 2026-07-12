<script lang="ts">
	import { ChevronLeft, ChevronRight } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	let {
		page,
		pageSize,
		total,
		onchange
	}: { page: number; pageSize: number; total: number; onchange: (page: number) => void } = $props();
	const pages = $derived(Math.max(1, Math.ceil(total / pageSize)));
</script>

<div class="flex items-center justify-between text-xs text-text-muted">
	<span class="tabular-nums">{total} records</span>
	<div class="flex items-center gap-2">
		<Button
			variant="outline"
			size="sm"
			aria-label="Previous page"
			disabled={page <= 1}
			onclick={() => onchange(page - 1)}><ChevronLeft size={14} />Prev</Button
		><span class="tabular-nums">Page {page} / {pages}</span><Button
			variant="outline"
			size="sm"
			aria-label="Next page"
			disabled={page >= pages}
			onclick={() => onchange(page + 1)}>Next<ChevronRight size={14} /></Button
		>
	</div>
</div>
