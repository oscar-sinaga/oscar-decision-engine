<script lang="ts">
	import { resolveStatus, type StatusTone } from './status';
	import { cn } from '$lib/utils';
	let { value, class: className = '' }: { value: string; class?: string } = $props();
	const definition = $derived(resolveStatus(value));
	const toneClass: Record<StatusTone, string> = {
		success: 'border-success/25 bg-success-bg text-text',
		warning: 'border-warning/25 bg-warning-bg text-text',
		danger: 'border-danger/25 bg-danger-bg text-text',
		info: 'border-info/25 bg-info-bg text-text',
		special: 'border-special/25 bg-special-bg text-text',
		neutral: 'border-neutral/20 bg-neutral-bg text-text'
	};
	const iconClass: Record<StatusTone, string> = {
		success: 'text-success',
		warning: 'text-warning',
		danger: 'text-danger',
		info: 'text-info',
		special: 'text-special',
		neutral: 'text-neutral'
	};
</script>

<span
	class={cn(
		'inline-flex items-center gap-1 rounded-control border px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap',
		toneClass[definition.tone],
		className
	)}
>
	<definition.icon size={12} class={iconClass[definition.tone]} aria-hidden="true" />
	{definition.label}
</span>
