<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { ChevronDown, Menu, PanelLeft } from '@lucide/svelte';
	import { auth } from '$lib/auth.svelte';
	import { Button } from '$lib/components/ui/button';
	import * as Breadcrumb from '$lib/components/ui/breadcrumb';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { breadcrumbs } from './breadcrumb.svelte';

	let {
		onMenu,
		onCollapse,
		collapsed = false
	}: {
		onMenu: () => void;
		onCollapse: () => void;
		collapsed?: boolean;
	} = $props();

	const labels: Record<string, string> = {
		dashboard: 'Dashboard',
		decisions: 'Decisions',
		rules: 'Rules',
		'decision-tables': 'Decision Tables',
		features: 'Feature Catalog',
		strategies: 'Strategies',
		simulations: 'Simulations',
		batch: 'Batch',
		models: 'Model Registry',
		'manual-review': 'Manual Review',
		audit: 'Audit Log',
		admin: 'Admin',
		new: 'New'
	};

	const routeParts = $derived(page.url.pathname.split('/').filter(Boolean));
	const section = $derived.by(() => {
		const first = routeParts[0] ?? '';
		if (['dashboard', 'decisions'].includes(first)) return 'Monitor';
		if (['rules', 'decision-tables', 'strategies', 'features', 'models'].includes(first)) {
			return 'Author';
		}
		if (['simulations', 'manual-review'].includes(first)) return 'Operate';
		if (['audit', 'admin'].includes(first)) return 'Govern';
		return 'Workspace';
	});
	const current = $derived(labels[routeParts[0] ?? ''] ?? 'Workspace');
	const detail = $derived.by(() => {
		if (breadcrumbs.entityLabel) return breadcrumbs.entityLabel;
		if (routeParts.length > 1) return labels[routeParts.at(-1) ?? ''] ?? routeParts.at(-1) ?? null;
		return null;
	});

	function logout(): void {
		auth.logout();
		goto('/login');
	}
</script>

<header
	class="sticky top-0 z-30 flex h-14 items-center border-b border-border bg-surface px-4 shadow-card"
>
	<div class="flex min-w-0 flex-1 items-center gap-2">
		<Button
			variant="ghost"
			size="icon-sm"
			class="md:hidden"
			onclick={onMenu}
			aria-label="Open navigation"
		>
			<Menu size={18} />
		</Button>
		<Button
			variant="ghost"
			size="icon-sm"
			class="hidden md:inline-flex"
			onclick={onCollapse}
			aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
			title={collapsed ? 'Expand navigation' : 'Collapse navigation'}
		>
			<PanelLeft size={18} />
		</Button>

		<Breadcrumb.Root class="min-w-0">
			<Breadcrumb.List class="flex-nowrap overflow-hidden text-xs">
				<Breadcrumb.Item class="hidden sm:inline-flex">
					<Breadcrumb.Link href="/dashboard">{section}</Breadcrumb.Link>
				</Breadcrumb.Item>
				<Breadcrumb.Separator class="hidden sm:block" />
				<Breadcrumb.Item>
					{#if detail}
						<Breadcrumb.Link href={`/${routeParts[0] ?? 'dashboard'}`}>{current}</Breadcrumb.Link>
					{:else}
						<Breadcrumb.Page>{current}</Breadcrumb.Page>
					{/if}
				</Breadcrumb.Item>
				{#if detail}
					<Breadcrumb.Separator />
					<Breadcrumb.Item class="min-w-0">
						<Breadcrumb.Page class="max-w-[280px] truncate font-mono">{detail}</Breadcrumb.Page>
					</Breadcrumb.Item>
				{/if}
			</Breadcrumb.List>
		</Breadcrumb.Root>
	</div>

	<div class="flex items-center gap-3">
		<span
			class="rounded-control bg-special-bg px-2 py-0.5 text-[10px] font-semibold tracking-wide text-special"
		>
			DEMO
		</span>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger
				class="flex items-center gap-2 rounded-control px-2 py-1.5 text-left hover:bg-surface-sunken focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:outline-none"
			>
				<span
					class="flex size-7 items-center justify-center rounded-full bg-primary-100 text-xs font-semibold text-primary-700"
				>
					{auth.user?.full_name?.slice(0, 1).toUpperCase() ?? 'U'}
				</span>
				<span class="hidden max-w-40 sm:block">
					<span class="block truncate text-xs font-semibold text-text"
						>{auth.user?.full_name ?? 'User'}</span
					>
					<span class="block truncate text-[10px] text-text-muted"
						>{auth.user?.roles.join(', ') ?? ''}</span
					>
				</span>
				<ChevronDown size={14} class="text-text-muted" />
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end" class="w-56">
				<DropdownMenu.Label>
					<div class="font-medium">{auth.user?.full_name ?? 'User'}</div>
					<div class="text-xs font-normal text-text-muted">{auth.user?.username ?? ''}</div>
				</DropdownMenu.Label>
				<DropdownMenu.Separator />
				<DropdownMenu.Item onclick={logout}>Sign out</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</div>
</header>
