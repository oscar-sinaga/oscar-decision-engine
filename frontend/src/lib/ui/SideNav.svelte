<script lang="ts">
	import { page } from '$app/state';
	import {
		BookOpen,
		Boxes,
		FileSearch,
		FlaskConical,
		GitBranch,
		Inbox,
		LayoutDashboard,
		ScrollText,
		Settings2,
		SquareFunction,
		Table2
	} from '@lucide/svelte';
	import { cn } from '$lib/utils';

	let {
		collapsed = false,
		onNavigate
	}: {
		collapsed?: boolean;
		onNavigate?: () => void;
	} = $props();

	const groups = [
		{
			label: 'Monitor',
			items: [
				{ href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
				{ href: '/decisions', label: 'Decisions', icon: FileSearch }
			]
		},
		{
			label: 'Author',
			items: [
				{ href: '/rules', label: 'Rules', icon: SquareFunction },
				{ href: '/decision-tables', label: 'Decision Tables', icon: Table2 },
				{ href: '/strategies', label: 'Strategies', icon: GitBranch },
				{ href: '/features', label: 'Feature Catalog', icon: BookOpen },
				{ href: '/models', label: 'Model Registry', icon: Boxes }
			]
		},
		{
			label: 'Operate',
			items: [
				{ href: '/simulations', label: 'Simulations', icon: FlaskConical },
				{ href: '/manual-review', label: 'Manual Review', icon: Inbox }
			]
		},
		{
			label: 'Govern',
			items: [
				{ href: '/audit', label: 'Audit Log', icon: ScrollText },
				{ href: '/admin', label: 'Admin', icon: Settings2 }
			]
		}
	];

	function isActive(href: string): boolean {
		return page.url.pathname === href || page.url.pathname.startsWith(`${href}/`);
	}
</script>

<nav
	class="flex-1 overflow-y-auto px-2 py-3"
	data-testid="main-nav"
	aria-label="Primary navigation"
>
	{#each groups as group (group.label)}
		<section class="mb-4">
			{#if !collapsed}
				<p class="mb-1 px-2 text-[10px] font-semibold tracking-[0.14em] text-text-faint uppercase">
					{group.label}
				</p>
			{/if}
			<div class="space-y-0.5">
				{#each group.items as item (item.href)}
					<a
						href={item.href}
						onclick={onNavigate}
						aria-current={isActive(item.href) ? 'page' : undefined}
						title={collapsed ? item.label : undefined}
						class={cn(
							'relative flex h-9 items-center gap-3 rounded-control border-l-2 px-2.5 text-[13px] font-medium transition focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-1 focus-visible:outline-none',
							isActive(item.href)
								? 'border-primary-600 bg-primary-50 text-primary-700'
								: 'border-transparent text-text-muted hover:bg-surface-sunken hover:text-text',
							collapsed && 'justify-center px-0'
						)}
					>
						<item.icon size={17} aria-hidden="true" />
						{#if !collapsed}<span>{item.label}</span>{/if}
					</a>
				{/each}
			</div>
		</section>
	{/each}
</nav>
