<script lang="ts">
	import { resolveStatus, type StatusTone } from './status';
	import { cn } from '$lib/utils';
	let { value, class: className = '' }: { value: string; class?: string } = $props();
	const definition = $derived(resolveStatus(value));
	const toneClass: Record<StatusTone, string> = {
		success: 'bg-success-bg text-success',
		warning: 'bg-warning-bg text-warning',
		danger: 'bg-danger-bg text-danger',
		info: 'bg-info-bg text-info',
		special: 'bg-special-bg text-special',
		neutral: 'bg-neutral-bg text-neutral'
	};
</script>

<span
	class={cn(
		'inline-flex items-center gap-1 rounded-control px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap',
		toneClass[definition.tone],
		className
	)}
>
	<definition.icon size={12} aria-hidden="true" />
	{definition.label}
</span>
