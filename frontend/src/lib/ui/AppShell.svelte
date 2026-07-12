<script lang="ts">
	import type { Snippet } from 'svelte';
	import { ChevronLeft, ChevronRight } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import SideNav from './SideNav.svelte';
	import TopBar from './TopBar.svelte';

	let { children }: { children: Snippet } = $props();
	let collapsed = $state(false);
	let mobileOpen = $state(false);

	$effect(() => {
		if (typeof localStorage === 'undefined') return;
		collapsed = localStorage.getItem('oscar.sidebar') === 'collapsed';
	});

	function toggleCollapse(): void {
		collapsed = !collapsed;
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem('oscar.sidebar', collapsed ? 'collapsed' : 'expanded');
		}
	}
</script>

<div
	class="grid min-h-screen bg-surface-muted transition-[grid-template-columns] duration-200 md:grid-cols-[var(--sidebar-width)_minmax(0,1fr)]"
	style={`--sidebar-width:${collapsed ? '56px' : '240px'}`}
>
	<aside class="hidden min-h-screen border-r border-border bg-surface md:flex md:flex-col">
		<div class="flex h-14 items-center border-b border-border px-3">
			<div class="flex min-w-0 flex-1 items-center gap-2">
				<div
					class="flex size-8 shrink-0 items-center justify-center rounded-control bg-primary-600 text-sm font-bold text-white"
				>
					O
				</div>
				{#if !collapsed}
					<div class="min-w-0">
						<div class="text-sm font-bold tracking-wide text-text">OSCAR</div>
						<div class="truncate text-[10px] text-text-muted">Decision Engine</div>
					</div>
				{/if}
			</div>
		</div>
		<SideNav {collapsed} />
		<div class="border-t border-border p-2">
			<Button
				variant="ghost"
				size={collapsed ? 'icon-sm' : 'sm'}
				class={collapsed ? 'w-full' : 'w-full justify-between'}
				onclick={toggleCollapse}
				aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
			>
				{#if !collapsed}<span class="text-xs">local</span>{/if}
				{#if collapsed}<ChevronRight size={15} />{:else}<ChevronLeft size={15} />{/if}
			</Button>
		</div>
	</aside>

	<div class="min-w-0">
		<TopBar onMenu={() => (mobileOpen = true)} onCollapse={toggleCollapse} {collapsed} />
		<main class="mx-auto w-full max-w-[1440px] p-4 md:p-6">
			{@render children()}
		</main>
	</div>
</div>

{#if mobileOpen}
	<div class="fixed inset-0 z-50 md:hidden">
		<button
			type="button"
			class="absolute inset-0 bg-text/40"
			onclick={() => (mobileOpen = false)}
			aria-label="Close navigation"
		></button>
		<aside
			class="relative flex h-full w-[280px] flex-col border-r border-border bg-surface shadow-overlay"
		>
			<div class="flex h-14 items-center gap-2 border-b border-border px-4">
				<div
					class="flex size-8 items-center justify-center rounded-control bg-primary-600 text-sm font-bold text-white"
				>
					O
				</div>
				<div>
					<div class="text-sm font-bold tracking-wide">OSCAR</div>
					<div class="text-[10px] text-text-muted">Decision Engine</div>
				</div>
			</div>
			<SideNav onNavigate={() => (mobileOpen = false)} />
		</aside>
	</div>
{/if}
