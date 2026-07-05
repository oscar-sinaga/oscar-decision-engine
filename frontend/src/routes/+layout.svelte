<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { auth } from '$lib/auth.svelte';

	let { children } = $props();

	const NAV = [
		{ href: '/dashboard', label: 'Dashboard' },
		{ href: '/decisions', label: 'Decisions' },
		{ href: '/rules', label: 'Rules' },
		{ href: '/features', label: 'Feature Catalog' },
		{ href: '/strategies', label: 'Strategies' },
		{ href: '/simulations', label: 'Simulations' },
		{ href: '/models', label: 'Model Registry' },
		{ href: '/manual-review', label: 'Manual Review' },
		{ href: '/audit', label: 'Audit Log' },
		{ href: '/admin', label: 'Admin' }
	];

	auth.initialize();

	$effect(() => {
		const path = page.url.pathname;
		if (!auth.isAuthenticated && path !== '/login') {
			goto('/login');
		} else if (auth.isAuthenticated && !auth.user) {
			auth.loadProfile().catch(() => auth.logout());
		}
	});

	function logout() {
		auth.logout();
		goto('/login');
	}
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

{#if page.url.pathname === '/login'}
	{@render children()}
{:else if auth.isAuthenticated}
	<div class="flex min-h-screen bg-slate-100">
		<aside class="flex w-52 shrink-0 flex-col border-r border-slate-200 bg-slate-900">
			<div class="px-4 py-4">
				<span class="text-lg font-bold tracking-wide text-white">OSCAR</span>
				<span class="block text-[11px] text-slate-400">Decision Engine Workbench</span>
			</div>
			<nav class="flex-1 space-y-0.5 px-2" data-testid="main-nav">
				{#each NAV as item (item.href)}
					<a
						href={item.href}
						class="block rounded px-3 py-2 text-sm {page.url.pathname.startsWith(item.href)
							? 'bg-slate-700 font-semibold text-white'
							: 'text-slate-300 hover:bg-slate-800 hover:text-white'}"
					>
						{item.label}
					</a>
				{/each}
			</nav>
			<div class="border-t border-slate-800 px-4 py-3 text-xs text-slate-400">
				{#if auth.user}
					<div class="font-medium text-slate-200">{auth.user.full_name}</div>
					<div class="mb-2">{auth.user.roles.join(', ')}</div>
				{/if}
				<button class="text-slate-300 underline hover:text-white" onclick={logout}>
					Sign out
				</button>
			</div>
		</aside>
		<main class="min-w-0 flex-1 p-6">
			{@render children()}
		</main>
	</div>
{/if}
