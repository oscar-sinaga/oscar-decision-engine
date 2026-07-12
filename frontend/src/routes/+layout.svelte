<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { auth } from '$lib/auth.svelte';
	import { Toaster } from '$lib/components/ui/sonner';
	import AppShell from '$lib/ui/AppShell.svelte';
	import ConfirmDialog from '$lib/ui/ConfirmDialog.svelte';
	import { setBreadcrumb } from '$lib/ui/breadcrumb.svelte';

	let { children } = $props();
	auth.initialize();

	$effect(() => {
		const path = page.url.pathname;
		setBreadcrumb(null);
		if (!auth.isAuthenticated && path !== '/login') {
			goto('/login');
		} else if (auth.isAuthenticated && !auth.user) {
			auth.loadProfile().catch(() => auth.logout());
		}
	});
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

{#if page.url.pathname === '/login'}
	{@render children()}
{:else if auth.isAuthenticated}
	<AppShell>{@render children()}</AppShell>
{/if}

<Toaster position="top-right" richColors />
<ConfirmDialog />
