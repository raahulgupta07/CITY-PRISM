<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { api, ROLE_LABELS } from '$lib/api';
	import { loadSession, session } from '$lib/session.svelte';

	let { children } = $props();
	let error = $state('');

	onMount(async () => {
		try {
			if (!(await loadSession())) await goto(resolve('/signin'));
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	});

	async function signOut() {
		await api('/auth/logout', { method: 'POST' });
		session.user = null;
		await goto(resolve('/signin'));
	}

	const mine = $derived(page.url.searchParams.get('mine') === '1');
	const nav = $derived([
		{ href: resolve('/'), label: 'Portfolio', on: page.url.pathname === '/' && !mine },
		{ href: resolve('/?mine=1'), label: 'My projects', on: page.url.pathname === '/' && mine },
		...(session.user?.role === 'admin'
			? [{ href: resolve('/admin'), label: 'Admin', on: page.url.pathname.startsWith('/admin') }]
			: [])
	]);
</script>

<a
	href="#main"
	class="sr-only z-50 bg-white p-3 text-ink focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
	>Skip to content</a
>
<header class="border-b border-[#1C2A40] bg-navy text-[#E6ECF2]">
	<div class="flex min-h-12 flex-wrap items-center gap-x-6 px-4 sm:px-5">
		<a
			href={resolve('/')}
			class="font-condensed text-base font-semibold tracking-[0.06em] text-white uppercase no-underline"
			>City Prism</a
		>
		<nav aria-label="Main" class="flex flex-1 gap-1 self-stretch">
			{#each nav as item (item.label)}
				<a
					href={item.href}
					aria-current={item.on ? 'page' : undefined}
					class="flex min-h-11 items-center px-3 text-sm no-underline {item.on
						? 'text-white shadow-[inset_0_-2px_0_var(--color-teal-on-dark)]'
						: 'text-[#AEB9C6] hover:text-white'}">{item.label}</a
				>
			{/each}
		</nav>
		{#if session.user}
			<div class="flex items-center gap-3 text-sm">
				<span>{session.user.name} · {ROLE_LABELS[session.user.role].toLowerCase()}</span>
				<button
					class="min-h-11 px-2 text-teal-on-dark underline-offset-4 hover:underline"
					onclick={signOut}>Sign out</button
				>
			</div>
		{/if}
	</div>
</header>

<div id="main">
	{#if error}
		<p role="alert" class="m-6 border-l-4 border-weak bg-panel p-4">{error}</p>
	{:else if session.user}
		{@render children()}
	{:else}
		<p class="p-6 text-muted">Loading…</p>
	{/if}
</div>
